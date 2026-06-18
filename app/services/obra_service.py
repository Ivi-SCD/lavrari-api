"""Serviço de gestão de obras e vínculos de usuários."""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.globals.models.obra.obra import Obra
from app.globals.models.obra_usuario.obra_usuario import ObraUsuario
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.repositories.rdo_repository import RDORepository
from app.repositories.usuario_repository import UsuarioRepository


class ObraService:
    def __init__(self):
        self.repo = ObraRepository()
        self.obra_usuario_repo = ObraUsuarioRepository()
        self.usuario_repo = UsuarioRepository()
        self.empresa_repo = EmpresaRepository()
        self.rdo_repo = RDORepository()
        self.alerta_repo = AlertaRepository()

    async def listar_acessiveis(self, usuario: dict, skip: int = 0, limit: int = 100) -> list[dict]:
        if usuario.get("is_admin"):
            return await self.repo.listar({}, skip=skip, limit=limit)
        vinculos = await self.obra_usuario_repo.listar_por_usuario(usuario["id_usuario"])
        ids = [v["id_obra"] for v in vinculos]
        if not ids:
            return []
        return await self.repo.listar_por_ids(ids)

    async def buscar(self, id_obra: str) -> dict:
        obra = await self.repo.buscar_por_id(id_obra)
        if not obra:
            raise NotFoundError("Obra não encontrada.")
        return obra

    async def criar(self, dados: dict) -> dict:
        if not await self.empresa_repo.buscar_por_id(dados["id_empresa_contratada"]):
            raise ValidationError("Empresa contratada não encontrada.")
        if dados.get("id_empresa_supervisora") and not await self.empresa_repo.buscar_por_id(
            dados["id_empresa_supervisora"]
        ):
            raise ValidationError("Empresa supervisora não encontrada.")
        if not await self.usuario_repo.buscar_por_id(dados["id_fiscal_suape"]):
            raise ValidationError("Fiscal SUAPE não encontrado.")
        if dados.get("id_fiscal_externo") and not await self.usuario_repo.buscar_por_id(
            dados["id_fiscal_externo"]
        ):
            raise ValidationError("Fiscal externo não encontrado.")

        obra = Obra(id_obra=str(uuid.uuid4()), **dados)
        criada = await self.repo.criar(obra.model_dump())

        # Vincula automaticamente os fiscais à obra.
        await self._vincular_interno(criada["id_obra"], dados["id_fiscal_suape"], PerfilUsuario.FISCAL_SUAPE)
        if dados.get("id_fiscal_externo"):
            await self._vincular_interno(
                criada["id_obra"], dados["id_fiscal_externo"], PerfilUsuario.FISCAL_EXTERNO
            )
        return criada

    async def atualizar(self, id_obra: str, dados: dict) -> dict:
        await self.buscar(id_obra)
        dados = {k: v for k, v in dados.items() if v is not None}
        return await self.repo.atualizar(id_obra, dados)

    # ---- Vínculos Obra-Usuário ----

    async def _vincular_interno(
        self, id_obra: str, id_usuario: str, perfil: PerfilUsuario, permissoes_extras: dict | None = None
    ) -> dict:
        existente = await self.obra_usuario_repo.buscar_por_obra_e_usuario(id_obra, id_usuario)
        if existente:
            return existente
        vinculo = ObraUsuario(
            id_obra_usuario=str(uuid.uuid4()),
            id_obra=id_obra,
            id_usuario=id_usuario,
            perfil=perfil,
            permissoes_extras=permissoes_extras or {},
        )
        return await self.obra_usuario_repo.criar(vinculo.model_dump())

    async def vincular_usuario(
        self, id_obra: str, id_usuario: str, perfil: PerfilUsuario, permissoes_extras: dict | None = None
    ) -> dict:
        await self.buscar(id_obra)
        if not await self.usuario_repo.buscar_por_id(id_usuario):
            raise NotFoundError("Usuário não encontrado.")
        if await self.obra_usuario_repo.buscar_por_obra_e_usuario(id_obra, id_usuario):
            raise ConflictError("Usuário já vinculado a esta obra.")
        return await self._vincular_interno(id_obra, id_usuario, perfil, permissoes_extras)

    async def listar_usuarios(self, id_obra: str) -> list[dict]:
        await self.buscar(id_obra)
        return await self.obra_usuario_repo.listar_por_obra(id_obra)

    async def _buscar_vinculo(self, id_obra: str, id_usuario: str) -> dict:
        vinculo = await self.obra_usuario_repo.buscar_por_obra_e_usuario(id_obra, id_usuario)
        if not vinculo:
            raise NotFoundError("Vínculo usuário-obra não encontrado.")
        return vinculo

    async def atualizar_perfil(self, id_obra: str, id_usuario: str, perfil: PerfilUsuario) -> dict:
        vinculo = await self._buscar_vinculo(id_obra, id_usuario)
        return await self.obra_usuario_repo.atualizar(
            vinculo["id_obra_usuario"], {"perfil": perfil.value}
        )

    async def desvincular(self, id_obra: str, id_usuario: str) -> None:
        vinculo = await self._buscar_vinculo(id_obra, id_usuario)
        await self.obra_usuario_repo.deletar(vinculo["id_obra_usuario"])

    async def atualizar_permissoes(self, id_obra: str, id_usuario: str, permissoes: dict) -> dict:
        vinculo = await self._buscar_vinculo(id_obra, id_usuario)
        permissoes = {k: v for k, v in permissoes.items() if v is not None}
        if isinstance(permissoes.get("expira_em"), datetime):
            permissoes["expira_em"] = permissoes["expira_em"]
        atuais = dict(vinculo.get("permissoes_extras") or {})
        atuais.update(permissoes)
        return await self.obra_usuario_repo.atualizar(
            vinculo["id_obra_usuario"], {"permissoes_extras": atuais}
        )

    # ---- Dashboard ----

    async def dashboard(self, id_obra: str) -> dict:
        obra = await self.buscar(id_obra)
        por_status = await self.rdo_repo.contar_por_status(id_obra)
        total = sum(por_status.values())

        inicio = obra.get("data_inicio_execucao")
        if isinstance(inicio, datetime):
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=timezone.utc)
            dias_decorridos = max((datetime.now(timezone.utc) - inicio).days, 0)
        else:
            dias_decorridos = 0
        prazo = obra.get("prazo_contratual_dias") or 0
        percentual = round((dias_decorridos / prazo) * 100, 1) if prazo else 0.0

        alertas_abertos = await self.alerta_repo.contar({"id_obra": id_obra, "lido": False})

        return {
            "id_obra": id_obra,
            "total_rdos": total,
            "rdos_por_status": por_status,
            "dias_decorridos": dias_decorridos,
            "prazo_contratual_dias": prazo,
            "percentual_prazo": percentual,
            "total_alertas_abertos": alertas_abertos,
        }

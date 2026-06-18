"""Serviço de workflow: máquina de estados do RDO."""

from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import NotFoundError, PermissionDeniedError, StateError
from app.globals.enums.comentario.tipo_comentario import TipoComentario
from app.globals.enums.rdo.acao_versao import AcaoVersao
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.repositories.obra_repository import ObraRepository
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.repositories.rdo_repository import RDORepository
from app.services.comentario_service import ComentarioService
from app.services.versioning_service import VersioningService


class WorkflowService:
    def __init__(self):
        self.repo = RDORepository()
        self.obra_repo = ObraRepository()
        self.obra_usuario_repo = ObraUsuarioRepository()
        self.versioning = VersioningService()
        self.comentarios = ComentarioService()

    async def _carregar_rdo(self, id_rdo: str) -> dict:
        rdo = await self.repo.buscar_por_id(id_rdo)
        if not rdo:
            raise NotFoundError("RDO não encontrado.")
        return rdo

    async def _perfil_na_obra(self, id_obra: str, usuario: dict) -> Optional[str]:
        if usuario.get("is_admin"):
            return PerfilUsuario.ADMINISTRADOR.value
        vinculo = await self.obra_usuario_repo.buscar_por_obra_e_usuario(
            id_obra, usuario["id_usuario"]
        )
        return vinculo["perfil"] if vinculo else None

    def _exigir(self, perfil: Optional[str], permitidos: set[str], acao: str) -> None:
        if perfil not in permitidos:
            raise PermissionDeniedError(f"Sem permissão para {acao}.")

    def _exigir_status(self, rdo: dict, esperado: set[str], acao: str) -> None:
        if rdo["status"] not in esperado:
            raise StateError(
                f"Não é possível {acao}: RDO está em status '{rdo['status']}'."
            )

    async def _aplicar(
        self, id_rdo: str, mudancas: dict, acao: AcaoVersao, usuario: dict, justificativa=None
    ) -> dict:
        atualizado = await self.repo.atualizar(id_rdo, mudancas)
        await self.versioning.criar_versao(atualizado, acao, usuario, justificativa)
        return atualizado

    async def submeter_rdo(self, id_rdo: str, usuario: dict) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(rdo, {StatusRDO.RASCUNHO.value}, "submeter")
        perfil = await self._perfil_na_obra(rdo["id_obra"], usuario)
        permitido = perfil in {
            PerfilUsuario.ADMINISTRADOR.value,
            PerfilUsuario.FORNECEDOR.value,
        }
        if not permitido and perfil == PerfilUsuario.FISCAL_EXTERNO.value:
            permitido = await self.obra_usuario_repo.verificar_permissao_temporaria(
                rdo["id_obra"], usuario["id_usuario"], "pode_enviar_suape"
            )
        if not permitido:
            raise PermissionDeniedError("Sem permissão para submeter este RDO.")

        obra = await self.obra_repo.buscar_por_id(rdo["id_obra"])
        novo_status = (
            StatusRDO.REVISAO_EXTERNA.value
            if obra and obra.get("id_fiscal_externo")
            else StatusRDO.REVISAO_SUAPE.value
        )
        return await self._aplicar(
            id_rdo,
            {"status": novo_status, "enviado_em": datetime.now(timezone.utc)},
            AcaoVersao.ENVIO_REVISAO,
            usuario,
        )

    async def aprovar_externo(self, id_rdo: str, usuario: dict) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(rdo, {StatusRDO.REVISAO_EXTERNA.value}, "aprovar (externo)")
        perfil = await self._perfil_na_obra(rdo["id_obra"], usuario)
        self._exigir(
            perfil,
            {PerfilUsuario.ADMINISTRADOR.value, PerfilUsuario.FISCAL_EXTERNO.value},
            "aprovar como fiscal externo",
        )
        return await self._aplicar(
            id_rdo,
            {"status": StatusRDO.REVISAO_SUAPE.value},
            AcaoVersao.APROVACAO_EXTERNA,
            usuario,
        )

    async def reprovar_externo(self, id_rdo: str, usuario: dict, motivo: str) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(rdo, {StatusRDO.REVISAO_EXTERNA.value}, "reprovar (externo)")
        perfil = await self._perfil_na_obra(rdo["id_obra"], usuario)
        self._exigir(
            perfil,
            {PerfilUsuario.ADMINISTRADOR.value, PerfilUsuario.FISCAL_EXTERNO.value},
            "reprovar como fiscal externo",
        )
        await self.comentarios.adicionar(
            id_rdo, usuario["id_usuario"], motivo, TipoComentario.SOLICITACAO_CORRECAO
        )
        return await self._aplicar(
            id_rdo,
            {"status": StatusRDO.RASCUNHO.value},
            AcaoVersao.REPROVACAO_EXTERNA,
            usuario,
            justificativa=motivo,
        )

    async def aprovar_suape(self, id_rdo: str, usuario: dict) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(rdo, {StatusRDO.REVISAO_SUAPE.value}, "aprovar (SUAPE)")
        perfil = await self._perfil_na_obra(rdo["id_obra"], usuario)
        self._exigir(
            perfil,
            {PerfilUsuario.ADMINISTRADOR.value, PerfilUsuario.FISCAL_SUAPE.value},
            "aprovar como fiscal SUAPE",
        )
        # APROVADO → BLOQUEADO automático.
        return await self._aplicar(
            id_rdo,
            {
                "status": StatusRDO.BLOQUEADO.value,
                "aprovado_em": datetime.now(timezone.utc),
            },
            AcaoVersao.APROVACAO_SUAPE,
            usuario,
        )

    async def reprovar_suape(self, id_rdo: str, usuario: dict, motivo: str) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(rdo, {StatusRDO.REVISAO_SUAPE.value}, "reprovar (SUAPE)")
        perfil = await self._perfil_na_obra(rdo["id_obra"], usuario)
        self._exigir(
            perfil,
            {PerfilUsuario.ADMINISTRADOR.value, PerfilUsuario.FISCAL_SUAPE.value},
            "reprovar como fiscal SUAPE",
        )
        await self.comentarios.adicionar(
            id_rdo, usuario["id_usuario"], motivo, TipoComentario.SOLICITACAO_CORRECAO
        )
        return await self._aplicar(
            id_rdo,
            {"status": StatusRDO.RASCUNHO.value},
            AcaoVersao.REPROVACAO_SUAPE,
            usuario,
            justificativa=motivo,
        )

    async def reabrir_rdo(self, id_rdo: str, usuario: dict, justificativa: str) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(
            rdo, {StatusRDO.BLOQUEADO.value, StatusRDO.FINALIZADO.value}, "reabrir"
        )
        perfil = await self._perfil_na_obra(rdo["id_obra"], usuario)
        self._exigir(
            perfil,
            {PerfilUsuario.ADMINISTRADOR.value, PerfilUsuario.FISCAL_SUAPE.value},
            "reabrir o RDO",
        )
        if not justificativa or not justificativa.strip():
            raise StateError("Justificativa é obrigatória para reabertura.")
        return await self._aplicar(
            id_rdo,
            {"status": StatusRDO.RASCUNHO.value, "aprovado_em": None},
            AcaoVersao.REABERTURA,
            usuario,
            justificativa=justificativa,
        )

    async def finalizar_rdo(self, id_rdo: str, usuario: dict) -> dict:
        rdo = await self._carregar_rdo(id_rdo)
        self._exigir_status(rdo, {StatusRDO.BLOQUEADO.value}, "finalizar")
        if not usuario.get("is_admin"):
            raise PermissionDeniedError("Apenas administradores podem finalizar RDOs.")
        return await self._aplicar(
            id_rdo,
            {"status": StatusRDO.FINALIZADO.value},
            AcaoVersao.FINALIZACAO,
            usuario,
        )

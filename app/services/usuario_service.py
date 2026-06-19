"""Serviço de gestão de usuários."""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_senha
from app.globals.models.usuario.usuario import Usuario
from app.repositories.obra_repository import ObraRepository
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.repositories.usuario_repository import UsuarioRepository

_PERMISSOES_CONHECIDAS = ("pode_adicionar_info", "pode_comentar", "pode_enviar_suape")


class UsuarioService:
    def __init__(self):
        self.repo = UsuarioRepository()
        self.obra_usuario_repo = ObraUsuarioRepository()
        self.obra_repo = ObraRepository()

    async def listar(self, skip: int = 0, limit: int = 100) -> list[dict]:
        return await self.repo.listar({}, skip=skip, limit=limit, ordenar=[("nome", 1)])

    async def criar(self, nome: str, email: str, senha: str, is_admin: bool = False) -> dict:
        if await self.repo.buscar_por_email(email):
            raise ConflictError("Já existe um usuário com este e-mail.")
        usuario = Usuario(
            id_usuario=str(uuid.uuid4()),
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
            is_admin=is_admin,
        )
        return await self.repo.criar(usuario.model_dump())

    async def buscar(self, id_usuario: str) -> dict:
        usuario = await self.repo.buscar_por_id(id_usuario)
        if not usuario:
            raise NotFoundError("Usuário não encontrado.")
        return usuario

    async def atualizar(self, id_usuario: str, dados: dict) -> dict:
        await self.buscar(id_usuario)
        dados = {k: v for k, v in dados.items() if v is not None}
        if "email" in dados:
            existente = await self.repo.buscar_por_email(dados["email"])
            if existente and existente["id_usuario"] != id_usuario:
                raise ConflictError("E-mail já utilizado por outro usuário.")
        return await self.repo.atualizar(id_usuario, dados)

    async def promover_admin(self, id_usuario: str) -> dict:
        await self.buscar(id_usuario)
        return await self.repo.atualizar(id_usuario, {"is_admin": True})

    @staticmethod
    def _parse_expira(extras: dict):
        expira = extras.get("expira_em")
        if isinstance(expira, str):
            try:
                expira = datetime.fromisoformat(expira.replace("Z", "+00:00"))
            except ValueError:
                return None
        if isinstance(expira, datetime) and expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        return expira

    async def listar_vinculos(self, id_usuario: str) -> list[dict]:
        """Lista os vínculos do usuário (perfil + permissões temporárias com expiração)
        em todas as obras — visão de governança de permissões para o admin."""
        await self.buscar(id_usuario)
        vinculos = await self.obra_usuario_repo.listar_por_usuario(id_usuario)
        agora = datetime.now(timezone.utc)
        resultado = []
        for v in vinculos:
            obra = await self.obra_repo.buscar_por_id(v["id_obra"])
            extras = dict(v.get("permissoes_extras") or {})
            expira = self._parse_expira(extras)
            vigente = expira is None or expira > agora
            ativas = [
                p for p in _PERMISSOES_CONHECIDAS if extras.get(p) and vigente
            ]
            resultado.append(
                {
                    "id_obra_usuario": v["id_obra_usuario"],
                    "id_obra": v["id_obra"],
                    "numero_contrato": obra.get("numero_contrato") if obra else None,
                    "objeto_contratual": obra.get("objeto_contratual") if obra else None,
                    "perfil": v["perfil"],
                    "permissoes_extras": extras,
                    "permissoes_ativas": ativas,
                    "expira_em": expira,
                    "criado_em": v["criado_em"],
                    "atualizado_em": v["atualizado_em"],
                }
            )
        return resultado

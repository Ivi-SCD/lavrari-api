"""Serviço de gestão de usuários."""

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_senha
from app.globals.models.usuario.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository


class UsuarioService:
    def __init__(self):
        self.repo = UsuarioRepository()

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

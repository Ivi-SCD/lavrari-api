"""Serviço de autenticação: usuários, tokens JWT e refresh tokens."""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import AuthError, ConflictError
from app.core.security import (
    JWTError,
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)
from app.globals.models.usuario.usuario import Usuario
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.usuario_repository import UsuarioRepository


class AuthService:
    def __init__(self):
        self.usuario_repo = UsuarioRepository()
        self.refresh_repo = RefreshTokenRepository()

    async def criar_usuario(
        self, nome: str, email: str, senha: str, is_admin: bool = False
    ) -> dict:
        if await self.usuario_repo.buscar_por_email(email):
            raise ConflictError("Já existe um usuário com este e-mail.")
        usuario = Usuario(
            id_usuario=str(uuid.uuid4()),
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
            is_admin=is_admin,
        )
        return await self.usuario_repo.criar(usuario.model_dump())

    async def autenticar(self, email: str, senha: str) -> tuple[str, str]:
        usuario = await self.usuario_repo.buscar_por_email(email)
        if not usuario or not verificar_senha(senha, usuario["senha_hash"]):
            raise AuthError("Credenciais inválidas.")
        return await self._emitir_tokens(usuario["id_usuario"], usuario["is_admin"])

    async def _emitir_tokens(self, id_usuario: str, is_admin: bool) -> tuple[str, str]:
        access = criar_access_token(id_usuario, {"is_admin": is_admin})
        refresh, expira_em = criar_refresh_token(id_usuario)
        await self.refresh_repo.criar(
            {
                "token": refresh,
                "id_usuario": id_usuario,
                "expira_em": expira_em,
                "revogado": False,
            }
        )
        return access, refresh

    async def renovar_token(self, refresh_token: str) -> str:
        try:
            payload = decodificar_token(refresh_token)
        except JWTError:
            raise AuthError("Refresh token inválido ou expirado.")
        if payload.get("type") != "refresh":
            raise AuthError("Token não é um refresh token.")

        registro = await self.refresh_repo.buscar_por_token(refresh_token)
        if not registro or registro.get("revogado"):
            raise AuthError("Refresh token revogado ou inexistente.")
        expira_em = registro["expira_em"]
        if expira_em.tzinfo is None:
            expira_em = expira_em.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expira_em:
            raise AuthError("Refresh token expirado.")

        usuario = await self.usuario_repo.buscar_por_id(payload["sub"])
        if not usuario:
            raise AuthError("Usuário não encontrado.")
        return criar_access_token(usuario["id_usuario"], {"is_admin": usuario["is_admin"]})

    async def invalidar_refresh_token(self, refresh_token: str) -> None:
        await self.refresh_repo.revogar(refresh_token)

    def verificar_token(self, token: str) -> dict:
        try:
            return decodificar_token(token)
        except JWTError:
            raise AuthError("Token inválido ou expirado.")

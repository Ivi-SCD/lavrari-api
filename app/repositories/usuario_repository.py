"""Repositório de Usuários."""

from typing import Optional

from app.repositories.base_repository import BaseRepository


class UsuarioRepository(BaseRepository):
    collection_name = "usuarios"
    id_field = "id_usuario"

    async def buscar_por_email(self, email: str) -> Optional[dict]:
        return await self.buscar_um({"email": email})

    async def existe_admin(self) -> bool:
        return await self.contar({"is_admin": True}) > 0

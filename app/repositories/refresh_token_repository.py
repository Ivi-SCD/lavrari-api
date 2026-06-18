"""Repositório de Refresh Tokens."""

from typing import Optional

from app.repositories.base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository):
    collection_name = "refresh_tokens"
    id_field = "token"

    async def buscar_por_token(self, token: str) -> Optional[dict]:
        return await self.buscar_um({"token": token})

    async def revogar(self, token: str) -> bool:
        res = await self.collection.update_one(
            {"token": token}, {"$set": {"revogado": True}}
        )
        return res.matched_count > 0

    async def revogar_do_usuario(self, id_usuario: str) -> int:
        res = await self.collection.update_many(
            {"id_usuario": id_usuario, "revogado": False},
            {"$set": {"revogado": True}},
        )
        return res.modified_count

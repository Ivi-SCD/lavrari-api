"""Repositório de Obras."""

from app.repositories.base_repository import BaseRepository


class ObraRepository(BaseRepository):
    collection_name = "obras"
    id_field = "id_obra"

    async def listar_por_ids(self, ids: list[str]) -> list[dict]:
        return await self.listar({"id_obra": {"$in": ids}}, limit=1000)

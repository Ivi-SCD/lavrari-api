"""Repositório de Mídias (fotos)."""

from datetime import datetime, timezone

from app.repositories.base_repository import BaseRepository


class MidiaRepository(BaseRepository):
    collection_name = "midias"
    id_field = "id_midia"

    async def listar_por_rdo(self, id_rdo: str) -> list[dict]:
        return await self.listar(
            {"id_rdo": id_rdo, "deletado_em": None},
            limit=1000,
            ordenar=[("criado_em", 1)],
        )

    async def listar_por_rdos(self, ids_rdo: list[str]) -> list[dict]:
        if not ids_rdo:
            return []
        return await self.listar(
            {"id_rdo": {"$in": ids_rdo}, "deletado_em": None},
            limit=5000,
            ordenar=[("data_hora_captura", 1)],
        )

    async def soft_delete(self, id_midia: str) -> bool:
        res = await self.collection.update_one(
            {"id_midia": id_midia, "deletado_em": None},
            {"$set": {"deletado_em": datetime.now(timezone.utc)}},
        )
        return res.modified_count > 0

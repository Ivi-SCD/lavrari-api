"""Repositório de RDOs."""

from app.repositories.base_repository import BaseRepository


class RDORepository(BaseRepository):
    collection_name = "rdos"
    id_field = "id_rdo"

    async def proximo_numero_registro(self, id_obra: str) -> int:
        doc = await self.collection.find_one(
            {"id_obra": id_obra}, sort=[("numero_registro", -1)]
        )
        return (doc["numero_registro"] + 1) if doc else 1

    async def listar_por_obra(self, id_obra: str, filtros: dict | None = None) -> list[dict]:
        query = {"id_obra": id_obra}
        if filtros:
            query.update(filtros)
        return await self.listar(query, limit=1000, ordenar=[("numero_registro", -1)])

    async def contar_por_status(self, id_obra: str) -> dict:
        pipeline = [
            {"$match": {"id_obra": id_obra}},
            {"$group": {"_id": "$status", "total": {"$sum": 1}}},
        ]
        resultado: dict = {}
        async for doc in self.collection.aggregate(pipeline):
            resultado[doc["_id"]] = doc["total"]
        return resultado

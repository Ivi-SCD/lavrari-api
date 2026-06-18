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

    async def contar_por_status_global(self) -> dict:
        pipeline = [{"$group": {"_id": "$status", "total": {"$sum": 1}}}]
        resultado: dict = {}
        async for doc in self.collection.aggregate(pipeline):
            resultado[doc["_id"]] = doc["total"]
        return resultado

    async def contar_com_restricao(self) -> int:
        """RDOs com ao menos uma flag de evento/restrição ativa."""
        flags = [
            "pessoal",
            "equipamento",
            "instalacoes",
            "cronograma_fisico",
            "qualidade",
            "atendimento_fiscalizacao",
            "administracao_obra",
            "meio_ambiente",
        ]
        ou = [{f"eventos_restricao.{f}": True} for f in flags]
        return await self.contar({"$or": ou})

    async def ids_por_obras(self, ids_obra: list[str]) -> list[str]:
        if not ids_obra:
            return []
        cursor = self.collection.find(
            {"id_obra": {"$in": ids_obra}}, {"id_rdo": 1, "_id": 0}
        )
        return [d["id_rdo"] async for d in cursor]

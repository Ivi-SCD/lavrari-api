"""Repositório de Alertas."""

from app.repositories.base_repository import BaseRepository


class AlertaRepository(BaseRepository):
    collection_name = "alertas"
    id_field = "id_alerta"

    async def listar_por_obra(self, id_obra: str, apenas_nao_lidos: bool = False) -> list[dict]:
        filtros: dict = {"id_obra": id_obra}
        if apenas_nao_lidos:
            filtros["lido"] = False
        return await self.listar(filtros, limit=1000, ordenar=[("criado_em", -1)])

    async def listar_por_obras(self, ids_obra: list[str]) -> list[dict]:
        return await self.listar(
            {"id_obra": {"$in": ids_obra}}, limit=1000, ordenar=[("criado_em", -1)]
        )

    async def existe_alerta_aberto(self, id_obra: str, tipo: str) -> bool:
        return await self.contar({"id_obra": id_obra, "tipo": tipo, "lido": False}) > 0

    async def marcar_lido(self, id_alerta: str) -> bool:
        res = await self.collection.update_one(
            {"id_alerta": id_alerta}, {"$set": {"lido": True}}
        )
        return res.matched_count > 0

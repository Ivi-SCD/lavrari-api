"""Repositório de Versões de RDO (snapshots imutáveis)."""

from typing import Optional

from app.repositories.base_repository import BaseRepository


class RdoVersaoRepository(BaseRepository):
    collection_name = "rdo_versoes"
    id_field = "id_versao"

    async def listar_por_rdo(self, id_rdo: str) -> list[dict]:
        return await self.listar({"id_rdo": id_rdo}, limit=1000, ordenar=[("versao", 1)])

    async def buscar_versao(self, id_rdo: str, versao: int) -> Optional[dict]:
        return await self.buscar_um({"id_rdo": id_rdo, "versao": versao})

    async def proximo_numero_versao(self, id_rdo: str) -> int:
        doc = await self.collection.find_one({"id_rdo": id_rdo}, sort=[("versao", -1)])
        return (doc["versao"] + 1) if doc else 1

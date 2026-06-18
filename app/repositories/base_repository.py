"""Repositório base assíncrono sobre MongoDB (Motor)."""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.infrastructure.mongodb.manager import get_mongo_manager

logger = logging.getLogger(__name__)


class BaseRepository:
    collection_name: str = ""
    id_field: str = ""

    @property
    def collection(self):
        return get_mongo_manager().get_collection(self.collection_name)

    @staticmethod
    def _limpar(doc: Optional[dict]) -> Optional[dict]:
        if doc is not None:
            doc.pop("_id", None)
        return doc

    async def criar(self, dados: dict) -> dict:
        await self.collection.insert_one(dados)
        return self._limpar(dados)

    async def buscar_por_id(self, id: str) -> Optional[dict]:
        return self._limpar(await self.collection.find_one({self.id_field: id}))

    async def buscar_um(self, filtros: dict) -> Optional[dict]:
        return self._limpar(await self.collection.find_one(filtros))

    async def atualizar(self, id: str, dados: dict) -> Optional[dict]:
        dados = {k: v for k, v in dados.items() if v is not None}
        dados["atualizado_em"] = datetime.now(timezone.utc)
        await self.collection.update_one({self.id_field: id}, {"$set": dados})
        return await self.buscar_por_id(id)

    async def deletar(self, id: str) -> bool:
        res = await self.collection.delete_one({self.id_field: id})
        return res.deleted_count > 0

    async def listar(
        self,
        filtros: Optional[dict] = None,
        skip: int = 0,
        limit: int = 100,
        ordenar: Optional[list] = None,
    ) -> list[dict]:
        cursor = self.collection.find(filtros or {})
        if ordenar:
            cursor = cursor.sort(ordenar)
        cursor = cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._limpar(d) for d in docs]

    async def contar(self, filtros: Optional[dict] = None) -> int:
        return await self.collection.count_documents(filtros or {})

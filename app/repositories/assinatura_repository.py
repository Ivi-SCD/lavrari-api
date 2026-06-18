"""Repositório de Assinaturas eletrônicas."""

from typing import Optional

from app.repositories.base_repository import BaseRepository


class AssinaturaRepository(BaseRepository):
    collection_name = "assinaturas"
    id_field = "id_assinatura"

    async def listar_por_rdo(self, id_rdo: str) -> list[dict]:
        return await self.listar({"id_rdo": id_rdo}, limit=1000, ordenar=[("criado_em", 1)])

    async def buscar_por_rdo_e_usuario(self, id_rdo: str, id_usuario: str) -> Optional[dict]:
        return await self.buscar_um({"id_rdo": id_rdo, "id_usuario": id_usuario})

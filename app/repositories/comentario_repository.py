"""Repositório de Comentários."""

from app.repositories.base_repository import BaseRepository


class ComentarioRepository(BaseRepository):
    collection_name = "comentarios"
    id_field = "id_comentario"

    async def listar_por_rdo(self, id_rdo: str) -> list[dict]:
        return await self.listar(
            {"id_rdo": id_rdo}, limit=1000, ordenar=[("criado_em", 1)]
        )

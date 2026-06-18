"""Serviço de comentários de RDO."""

import uuid

from app.core.exceptions import NotFoundError
from app.globals.enums.comentario.tipo_comentario import TipoComentario
from app.globals.models.comentario.comentario import Comentario
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.rdo_repository import RDORepository


class ComentarioService:
    def __init__(self):
        self.repo = ComentarioRepository()
        self.rdo_repo = RDORepository()

    async def listar(self, id_rdo: str) -> list[dict]:
        if not await self.rdo_repo.buscar_por_id(id_rdo):
            raise NotFoundError("RDO não encontrado.")
        return await self.repo.listar_por_rdo(id_rdo)

    async def adicionar(
        self,
        id_rdo: str,
        id_usuario: str,
        conteudo: str,
        tipo: TipoComentario = TipoComentario.COMENTARIO,
    ) -> dict:
        comentario = Comentario(
            id_comentario=str(uuid.uuid4()),
            id_rdo=id_rdo,
            id_usuario=id_usuario,
            conteudo=conteudo,
            tipo=tipo,
        )
        return await self.repo.criar(comentario.model_dump())

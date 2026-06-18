"""Schemas de Comentário."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.globals.enums.comentario.tipo_comentario import TipoComentario


class ComentarioCreate(BaseModel):
    conteudo: str = Field(..., min_length=1)
    tipo: TipoComentario = TipoComentario.COMENTARIO


class ComentarioResponse(BaseModel):
    id_comentario: str
    id_rdo: str
    id_usuario: str
    conteudo: str
    tipo: TipoComentario
    criado_em: datetime
    atualizado_em: datetime

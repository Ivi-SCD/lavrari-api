from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime, timezone

from app.globals.enums.comentario.tipo_comentario import TipoComentario


class Comentario(BaseModel):
    id_comentario: str = Field(..., description="ID do Comentário")
    id_rdo: str = Field(..., description="ID do RDO vinculado")
    id_usuario: str = Field(..., description="ID do usuário que comentou")
    conteudo: str = Field(..., description="Conteúdo do comentário")
    tipo: TipoComentario = Field(..., description="Tipo do comentário")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

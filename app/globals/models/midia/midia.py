from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime, timezone

from app.globals.enums.midia.tipo_midia import TipoMidia


class Midia(BaseModel):
    id_midia: str = Field(..., description="ID da Mídia")
    id_rdo: str = Field(..., description="ID do RDO vinculado")
    tipo: TipoMidia = Field(..., description="Tipo da Mídia")
    storage_url: str = Field(..., description="URL do arquivo no storage")
    latitude: float = Field(..., description="Latitude da captura")
    longitude: float = Field(..., description="Longitude da captura")
    data_hora_captura: datetime = Field(..., description="Data e hora da captura")
    ai_analise: Optional[str] = Field(None, description="Análise gerada pela IA")
    criado_por: str = Field(..., description="ID do usuário que enviou a mídia")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

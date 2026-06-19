"""Schemas de Mídia."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.globals.enums.midia.tipo_midia import TipoMidia


class MidiaResponse(BaseModel):
    id_midia: str
    id_rdo: str
    tipo: TipoMidia
    storage_url: str
    latitude: float
    longitude: float
    endereco: Optional[str] = None
    data_hora_captura: datetime
    ai_analise: Optional[str] = None
    criado_por: str
    criado_em: datetime
    atualizado_em: datetime

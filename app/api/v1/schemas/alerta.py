"""Schemas de Alerta."""

from datetime import datetime

from pydantic import BaseModel

from app.globals.enums.alerta.tipo_alerta import SeveridadeAlerta, TipoAlerta


class AlertaResponse(BaseModel):
    id_alerta: str
    id_obra: str
    tipo: TipoAlerta
    severidade: SeveridadeAlerta
    descricao: str
    lido: bool
    criado_em: datetime
    atualizado_em: datetime

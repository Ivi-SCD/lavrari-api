"""Schemas de assinatura eletrônica e dossiê."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AssinarRequest(BaseModel):
    senha: str = Field(..., description="Senha do usuário para confirmar identidade")
    cargo: Optional[str] = Field(None, description="Cargo do assinante, ex: 'Engenheiro Civil'")
    papel: str = Field(..., description="CONSTRUTORA|SUPERVISORA|FISCAL_SUAPE|FISCAL_EXTERNO")


class AssinaturaResponse(BaseModel):
    id_assinatura: str
    id_rdo: str
    versao_rdo: int
    nome_completo: str
    email: str
    cargo: Optional[str] = None
    papel: str
    hash_documento: str
    pdf_url: str
    criado_em: datetime


class DossieRequest(BaseModel):
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None

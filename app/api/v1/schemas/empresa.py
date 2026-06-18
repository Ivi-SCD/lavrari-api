"""Schemas de Empresa."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmpresaCreate(BaseModel):
    razao_social: str = Field(..., min_length=2)
    cnpj: str = Field(..., min_length=11)
    logo_url: Optional[str] = None


class EmpresaUpdate(BaseModel):
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    logo_url: Optional[str] = None


class EmpresaResponse(BaseModel):
    id_empresa: str
    razao_social: str
    cnpj: str
    logo_url: Optional[str] = None
    criado_em: datetime
    atualizado_em: datetime

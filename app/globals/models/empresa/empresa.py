from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime, timezone


class Empresa(BaseModel):
    id_empresa: str = Field(..., description="ID da Empresa")
    razao_social: str = Field(..., description="Razão Social da Empresa")
    cnpj: str = Field(..., description="CNPJ da Empresa")
    logo_url: Optional[str] = Field(None, description="URL do Logo da Empresa")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

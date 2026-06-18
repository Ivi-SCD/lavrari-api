from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class Assinatura(BaseModel):
    id_assinatura: str = Field(..., description="ID da assinatura")
    id_rdo: str = Field(..., description="ID do RDO assinado")
    versao_rdo: int = Field(..., description="Versão do RDO no momento da assinatura")
    id_usuario: str = Field(..., description="ID do usuário que assinou")
    nome_completo: str = Field(..., description="Nome desnormalizado")
    email: str = Field(..., description="E-mail desnormalizado")
    cargo: Optional[str] = Field(None, description="Cargo do assinante")
    papel: str = Field(
        ..., description="CONSTRUTORA|SUPERVISORA|FISCAL_SUAPE|FISCAL_EXTERNO"
    )
    hash_documento: str = Field(..., description="SHA-256 do PDF gerado")
    ip_address: Optional[str] = Field(None)
    pdf_url: str = Field(..., description="URL do PDF assinado no COS")
    criado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

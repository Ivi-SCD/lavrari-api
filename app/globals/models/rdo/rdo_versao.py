from pydantic import BaseModel, Field
from typing import Optional, Any

from datetime import datetime, timezone

from app.globals.enums.rdo.acao_versao import AcaoVersao


class RdoVersao(BaseModel):
    id_versao: str = Field(..., description="ID da Versão")
    id_rdo: str = Field(..., description="ID do RDO vinculado")
    versao: int = Field(..., description="Número da versão")
    snapshot: dict[str, Any] = Field(..., description="Cópia completa do RDO neste momento")
    acao: AcaoVersao = Field(..., description="Ação que gerou esta versão")
    justificativa: Optional[str] = Field(None, description="Obrigatória em reabertura")
    pdf_url: Optional[str] = Field(
        None, description="URL no COS do PDF imutável desta versão do documento"
    )
    pdf_hash: Optional[str] = Field(
        None, description="SHA-256 do PDF imutável desta versão"
    )
    criado_por: str = Field(..., description="ID do usuário que executou a ação")
    criado_por_nome: str = Field(..., description="Nome do usuário preservado no momento da ação")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )

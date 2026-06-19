from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime, timezone


class ResponsavelObra(BaseModel):
    """Responsável técnico da obra. Pode haver mais de um e a composição muda
    ao longo do tempo — o histórico é preservado nos snapshots de versão do RDO."""

    nome: str = Field(..., description="Nome do responsável técnico")
    art: Optional[str] = Field(None, description="Número da ART/ARTT do responsável")
    cargo: Optional[str] = Field(None, description="Cargo/função na obra")
    documento: Optional[str] = Field(None, description="Registro profissional (CREA/CAU) ou CPF")


class Obra(BaseModel):
    id_obra: str = Field(..., description="ID da Obra")
    id_empresa_contratada: str = Field(..., description="ID da Empresa Contratada")
    id_empresa_supervisora: Optional[str] = Field(
        None, description="ID da Empresa Supervisora"
    )
    id_fiscal_suape: str = Field(..., description="ID do Fiscal do Suape")
    art_fiscal_suape: Optional[str] = Field(None, description="ART/ARTT do Fiscal SUAPE")
    id_fiscal_externo: Optional[str] = Field(None, description="ID do Fiscal Externo")
    art_fiscal_externo: Optional[str] = Field(None, description="ART/ARTT do Fiscal Externo")
    responsaveis: list[ResponsavelObra] = Field(
        default_factory=list,
        description="Responsáveis técnicos da obra (com ART) — podem mudar ao longo do tempo",
    )
    numero_contrato: str = Field(..., description="Número do Contrato")
    objeto_contratual: str = Field(..., description="Objeto do Contrato")
    tipologia: str = Field(..., description="Tipologia da Obra")
    local_descricao: str = Field(..., description="Descrição do Local da Obra")
    latitude_obra: Optional[float] = Field(None, description="Latitude da Obra")
    longitude_obra: Optional[float] = Field(None, description="Longitude da Obra")
    endereco: Optional[str] = Field(
        None, description="Endereço (logradouro) resolvido por geocodificação reversa"
    )
    data_inicio_vigencia: datetime = Field(
        ..., description="Data de Início da Vigência"
    )
    data_fim_vigencia: datetime = Field(..., description="Data de Fim")
    data_inicio_execucao: datetime = Field(
        ..., description="Data de Início da Execuçao"
    )
    data_fim_execucao: datetime = Field(..., description="Data de Fim da Execução")
    prazo_contratual_dias: int = Field(..., description="Prazo do Contrato em dias")
    logo_suape_url: Optional[str] = Field(None, description="URL do Logo do Suape")
    logo_contratada_url: Optional[str] = Field(
        None, description="URL do Logo da Empresa Contratada"
    )
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

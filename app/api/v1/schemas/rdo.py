"""Schemas de RDO e versões."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.globals.enums.rdo.acao_versao import AcaoVersao
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.globals.models.rdo.geral import (
    CondicaoClimatica,
    Equipamento,
    EventosRestricao,
    ItemPessoal,
    Servico,
)


class RDOCreate(BaseModel):
    id_obra: str
    data_relatorio: datetime
    clima_manha: Optional[CondicaoClimatica] = None
    clima_tarde: Optional[CondicaoClimatica] = None
    pessoal_direto: Optional[List[ItemPessoal]] = None
    pessoal_indireto: Optional[List[ItemPessoal]] = None
    equipamentos: Optional[List[Equipamento]] = None
    servicos: Optional[List[Servico]] = None
    eventos_restricao: Optional[EventosRestricao] = None
    ocorrencias: Optional[str] = None
    resumo_dia: Optional[str] = None


class RDOUpdate(BaseModel):
    data_relatorio: Optional[datetime] = None
    clima_manha: Optional[CondicaoClimatica] = None
    clima_tarde: Optional[CondicaoClimatica] = None
    pessoal_direto: Optional[List[ItemPessoal]] = None
    pessoal_indireto: Optional[List[ItemPessoal]] = None
    equipamentos: Optional[List[Equipamento]] = None
    servicos: Optional[List[Servico]] = None
    eventos_restricao: Optional[EventosRestricao] = None
    ocorrencias: Optional[str] = None
    resumo_dia: Optional[str] = None


class RDOResponse(BaseModel):
    id_rdo: str
    id_obra: str
    numero_registro: int
    data_relatorio: datetime
    status: StatusRDO
    clima_manha: Optional[CondicaoClimatica] = None
    clima_tarde: Optional[CondicaoClimatica] = None
    pessoal_direto: Optional[List[ItemPessoal]] = None
    pessoal_indireto: Optional[List[ItemPessoal]] = None
    equipamentos: Optional[List[Equipamento]] = None
    servicos: Optional[List[Servico]] = None
    eventos_restricao: Optional[EventosRestricao] = None
    ocorrencias: Optional[str] = None
    resumo_dia: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    enviado_em: Optional[datetime] = None
    criado_por: str
    criado_em: datetime
    atualizado_em: datetime


class MotivoRequest(BaseModel):
    motivo: str = Field(..., min_length=3)


class JustificativaRequest(BaseModel):
    justificativa: str = Field(..., min_length=3)


class RdoVersaoResponse(BaseModel):
    id_versao: str
    id_rdo: str
    versao: int
    snapshot: dict[str, Any]
    acao: AcaoVersao
    justificativa: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_hash: Optional[str] = None
    criado_por: str
    criado_por_nome: str
    criado_em: datetime

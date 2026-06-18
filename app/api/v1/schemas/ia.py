"""Schemas de endpoints de IA."""

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field


class TranscricaoResponse(BaseModel):
    texto: str


class SugestaoRequest(BaseModel):
    id_obra: str
    data_relatorio: datetime


class SugestaoResponse(BaseModel):
    ocorrencias: str
    resumo_dia: str


# ---- Diferencial 1: Saúde da Obra ----


class SaudeResponse(BaseModel):
    id_obra: str
    score: int
    classificacao: str
    breakdown: dict[str, Any]
    rdos_analisados: int
    periodo: str


# ---- Diferencial 3: Padrões de Não Conformidade ----


class PadraoNCItem(BaseModel):
    descricao: str
    severidade: str
    ocorrencias: int
    recomendacao: str


class PadroesNCResponse(BaseModel):
    id_obra: str
    padroes_detectados: List[PadraoNCItem]
    rdos_analisados: int
    gerado_em: datetime


# ---- Diferencial 4: Chat com os dados ----


class ChatMensagem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    mensagem: str = Field(..., min_length=1)
    historico: List[ChatMensagem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    resposta: str
    tools_usadas: List[str] = Field(default_factory=list)

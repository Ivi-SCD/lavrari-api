"""Schemas de endpoints de IA."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.globals.enums.rdo.fonte_dado_rdo import FonteDado


class TranscricaoResponse(BaseModel):
    texto: str


class SugestaoRequest(BaseModel):
    id_obra: str
    data_relatorio: datetime


class SugestaoResponse(BaseModel):
    ocorrencias: str
    resumo_dia: str


# ---- Estruturação de RDO a partir de fala/texto livre ----


class EstruturarRDORequest(BaseModel):
    id_obra: str
    data_relatorio: datetime
    texto: str = Field(..., min_length=1, description="Transcrição livre do dia")


class ClimaSugestao(BaseModel):
    tempo: str
    praticavel: bool
    fonte: FonteDado = FonteDado.TRANSCRICAO


class ItemPessoalSugestao(BaseModel):
    funcao: str
    quantidade: int


class EquipamentoSugestao(BaseModel):
    nome: str
    quantidade: int


class ServicoSugestao(BaseModel):
    descricao: str
    situacao: Optional[str] = None
    grupo: Optional[str] = None


class EventosRestricaoSugestao(BaseModel):
    pessoal: bool = False
    equipamento: bool = False
    instalacoes: bool = False
    cronograma_fisico: bool = False
    qualidade: bool = False
    atendimento_fiscalizacao: bool = False
    administracao_obra: bool = False
    meio_ambiente: bool = False
    descricao: Optional[str] = None


class EstruturarRDOResponse(BaseModel):
    """Espelha os campos editáveis do RDO. Todos opcionais — a IA preenche só o que
    inferiu; o frontend faz merge (não overwrite) e o usuário confirma com PATCH /rdos/{id}."""

    clima_manha: Optional[ClimaSugestao] = None
    clima_tarde: Optional[ClimaSugestao] = None
    pessoal_direto: Optional[List[ItemPessoalSugestao]] = None
    pessoal_indireto: Optional[List[ItemPessoalSugestao]] = None
    equipamentos: Optional[List[EquipamentoSugestao]] = None
    servicos: Optional[List[ServicoSugestao]] = None
    eventos_restricao: Optional[EventosRestricaoSugestao] = None
    ocorrencias: Optional[str] = None
    resumo_dia: Optional[str] = None
    # Metadados para UX (não fazem parte do RDO).
    campos_preenchidos: List[str] = Field(default_factory=list)
    confianca: float = 0.0
    transcricao: Optional[str] = None


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

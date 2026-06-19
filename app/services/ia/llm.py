"""Fábricas de modelos Groq (LangChain) e schemas de saída estruturada."""

import logging
from typing import Optional

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, SecretStr

from app.core.config.settings import get_settings
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)
settings = get_settings()

MODELO_TEXTO = "llama-3.3-70b-versatile"
MODELO_VISAO = "meta-llama/llama-4-scout-17b-16e-instruct"
MODELO_AGENTE = "openai/gpt-oss-120b"
MODELO_AUDIO = "whisper-large-v3"


def _guard() -> None:
    if not settings.GROQ_API_KEY:
        raise ServiceUnavailableError("IA indisponível: GROQ_API_KEY não configurada.")


_chats: dict[str, ChatGroq] = {}


def get_chat(model: str, temperature: float = 0.3) -> ChatGroq:
    """Retorna (e memoiza) uma instância ``ChatGroq`` por modelo/temperatura."""
    _guard()
    chave = f"{model}:{temperature}"
    if chave not in _chats:
        _chats[chave] = ChatGroq(
            model=model,
            temperature=temperature,
            api_key=SecretStr(settings.GROQ_API_KEY),
        )
    return _chats[chave]


_groq_client = None


def get_groq_client():
    """Cliente Groq cru — usado apenas para transcrição de áudio (whisper)."""
    _guard()
    global _groq_client
    if _groq_client is None:
        from groq import AsyncGroq

        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _groq_client


class PadraoNC(BaseModel):
    descricao: str = Field(
        ..., description="Descrição clara do padrão de não conformidade"
    )
    severidade: str = Field(..., description="baixa | media | alta | critica")
    ocorrencias: int = Field(0, description="Número de ocorrências detectadas")
    recomendacao: str = Field("", description="Recomendação prática de ação")


class PadroesNCLLM(BaseModel):
    padroes: list[PadraoNC] = Field(default_factory=list)


class SugestaoLLM(BaseModel):
    ocorrencias: str = Field(
        "", description="Sugestão para o campo de ocorrências do dia"
    )
    resumo_dia: str = Field("", description="Sugestão de resumo do dia")


# ---- Estruturação de RDO a partir de fala/texto livre ----


class ClimaLLM(BaseModel):
    tempo: str = Field("", description="Condição do tempo (ex.: Ensolarado, Chuvoso, Nublado)")
    praticavel: bool = Field(True, description="Se foi possível trabalhar neste período")


class ItemPessoalLLM(BaseModel):
    funcao: str = Field(..., description="Função (ex.: Pedreiro, Servente, Encarregado)")
    quantidade: int = Field(..., description="Quantidade de pessoas nesta função")


class EquipamentoLLM(BaseModel):
    nome: str = Field(..., description="Nome do equipamento")
    quantidade: int = Field(..., description="Quantidade do equipamento")


class ServicoLLM(BaseModel):
    descricao: str = Field(..., description="Descrição do serviço executado")
    situacao: str = Field("em andamento", description="Situação: em andamento, concluído, paralisado")
    grupo: Optional[str] = Field(None, description="Grupo/disciplina (ex.: Estrutura, Fundação)")


class EventosRestricaoLLM(BaseModel):
    pessoal: bool = False
    equipamento: bool = False
    instalacoes: bool = False
    cronograma_fisico: bool = False
    qualidade: bool = False
    atendimento_fiscalizacao: bool = False
    administracao_obra: bool = False
    meio_ambiente: bool = False
    descricao: Optional[str] = Field(None, description="Descrição da restrição/ocorrência impeditiva")


class EstruturaRDOLLM(BaseModel):
    """Extração estruturada do RDO a partir de uma fala/texto livre do dia."""

    clima_manha: Optional[ClimaLLM] = None
    clima_tarde: Optional[ClimaLLM] = None
    pessoal_direto: list[ItemPessoalLLM] = Field(default_factory=list)
    pessoal_indireto: list[ItemPessoalLLM] = Field(default_factory=list)
    equipamentos: list[EquipamentoLLM] = Field(default_factory=list)
    servicos: list[ServicoLLM] = Field(default_factory=list)
    eventos_restricao: Optional[EventosRestricaoLLM] = None
    ocorrencias: Optional[str] = Field(None, description="Ocorrências relevantes do dia")
    resumo_dia: Optional[str] = Field(None, description="Resumo narrativo do dia")
    confianca: float = Field(
        0.0, description="Autoavaliação de confiança da extração, de 0.0 a 1.0"
    )

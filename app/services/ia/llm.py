"""Fábricas de modelos Groq (LangChain) e schemas de saída estruturada."""

import logging

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

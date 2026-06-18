"""Diferencial 4 — Agente conversacional (LangChain create_agent + Groq gpt-oss-120b)."""

import logging
from typing import Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from app.core.exceptions import ServiceUnavailableError
from app.services.ia.llm import MODELO_AGENTE, get_chat, settings
from app.services.ia.tools import ToolContext, construir_tools

logger = logging.getLogger(__name__)

_SISTEMA = (
    "Você é o assistente inteligente do Lavrari, sistema de gestão de obras da SUAPE. "
    "Responda em português, de forma objetiva e técnica. Use as ferramentas disponíveis "
    "para consultar dados reais antes de responder. Nunca invente dados — sempre consulte "
    "as tools. Ao receber o resultado das ferramentas, interprete-o e responda diretamente "
    "à pergunta do usuário com base nesses dados."
)


class AgenteChatService:
    async def responder(
        self, mensagem: str, usuario: dict, historico: Optional[list[dict]] = None
    ) -> dict:
        if not settings.GROQ_API_KEY:
            raise ServiceUnavailableError("IA indisponível: GROQ_API_KEY não configurada.")

        ctx = ToolContext(usuario)
        agente = create_agent(
            get_chat(MODELO_AGENTE, 0.2),
            construir_tools(ctx),
            system_prompt=_SISTEMA,
        )

        mensagens: list = []
        for h in historico or []:
            if h.get("role") == "assistant":
                mensagens.append(AIMessage(content=h.get("content", "")))
            else:
                mensagens.append(HumanMessage(content=h.get("content", "")))
        mensagens.append(HumanMessage(content=mensagem))

        resultado = await agente.ainvoke(
            {"messages": mensagens}, {"recursion_limit": 12}
        )

        tools_usadas: list[str] = []
        resposta = ""
        for msg in resultado["messages"]:
            for tc in getattr(msg, "tool_calls", None) or []:
                nome = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if nome and nome not in tools_usadas:
                    tools_usadas.append(nome)
            if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
                resposta = msg.content.strip()

        return {"resposta": resposta, "tools_usadas": tools_usadas}

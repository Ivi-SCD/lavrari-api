"""Endpoints de IA: transcrição, sugestão, saúde, padrões de NC e agente."""

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.v1.deps import (
    get_ia_service,
    get_rdo_service,
    get_usuario_atual,
    requer_acesso_obra,
    requer_perfil_obra,
)
from app.api.v1.schemas.ia import (
    ChatRequest,
    ChatResponse,
    PadroesNCResponse,
    SaudeResponse,
    SugestaoRequest,
    SugestaoResponse,
    TranscricaoResponse,
)
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.services.ia import IAService
from app.services.rdo_service import RDOService

router = APIRouter(prefix="/ia", tags=["ia"])

_PERFIS_GESTAO = (PerfilUsuario.FISCAL_SUAPE,)


@router.post(
    "/transcricao",
    summary="Transcrever áudio",
    description="Recebe um arquivo de áudio e retorna o texto transcrito (Groq "
    "whisper-large-v3).",
    response_model=TranscricaoResponse,
    responses={
        200: {"description": "Texto transcrito"},
        503: {"description": "IA indisponível (GROQ_API_KEY ausente)"},
    },
)
async def transcricao(
    arquivo: UploadFile = File(...),
    _usuario: dict = Depends(get_usuario_atual),
    ia: IAService = Depends(get_ia_service),
):
    conteudo = await arquivo.read()
    texto = await ia.transcrever_audio(conteudo, arquivo.filename or "audio.m4a")
    return TranscricaoResponse(texto=texto)


@router.post(
    "/sugestao-texto",
    summary="Sugerir preenchimento do dia",
    description="Gera sugestões de 'ocorrencias' e 'resumo_dia' com base no histórico de "
    "RDOs da obra. Requer acesso à obra.",
    response_model=SugestaoResponse,
    responses={
        200: {"description": "Sugestão gerada"},
        403: {"description": "Sem acesso à obra"},
        503: {"description": "IA indisponível"},
    },
)
async def sugestao_texto(
    dados: SugestaoRequest,
    usuario_atual: dict = Depends(get_usuario_atual),
    ia: IAService = Depends(get_ia_service),
    rdo_service: RDOService = Depends(get_rdo_service),
):
    await requer_acesso_obra(dados.id_obra, usuario_atual)
    historico = await rdo_service.listar({"id_obra": dados.id_obra}, limit=15)
    resultado = await ia.sugerir_texto_rdo(dados.id_obra, dados.data_relatorio, historico)
    return SugestaoResponse(**resultado)


@router.get(
    "/saude-obra/{id_obra}",
    summary="Índice de Saúde da Obra",
    description="Calcula score 0-100 da obra baseado em restrições, tempo de aprovação, "
    "reprovações e prazo contratual. Atualizado em tempo real a partir dos últimos 30 RDOs. "
    "Restrito a Admin ou Fiscal SUAPE.",
    response_model=SaudeResponse,
    responses={
        200: {"description": "Score calculado com sucesso"},
        403: {"description": "Acesso restrito a admin e fiscal SUAPE"},
        404: {"description": "Obra não encontrada"},
    },
)
async def saude_obra(
    id_obra: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    ia: IAService = Depends(get_ia_service),
):
    await requer_perfil_obra(id_obra, usuario_atual, _PERFIS_GESTAO)
    return await ia.calcular_saude_obra(id_obra)


@router.get(
    "/padroes-nc/{id_obra}",
    summary="Detecção de Padrões de Não Conformidade",
    description="Usa IA (Groq llama-3.3-70b via LangChain) para analisar o histórico de RDOs "
    "e identificar padrões recorrentes que humanos dificilmente perceberiam. Os resultados são "
    "salvos como alertas da obra. Restrito a Admin ou Fiscal SUAPE.",
    response_model=PadroesNCResponse,
    responses={
        200: {"description": "Padrões detectados"},
        403: {"description": "Acesso restrito a admin e fiscal SUAPE"},
        404: {"description": "Obra não encontrada"},
        503: {"description": "IA indisponível"},
    },
)
async def padroes_nc(
    id_obra: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    ia: IAService = Depends(get_ia_service),
):
    await requer_perfil_obra(id_obra, usuario_atual, _PERFIS_GESTAO)
    return await ia.detectar_padroes_nc(id_obra)


@router.post(
    "/chat",
    summary="Chat com os Dados das Obras",
    description="Agente conversacional (LangGraph ReAct + Groq gpt-oss-120b) com acesso às "
    "tools de consulta do sistema. Responde perguntas sobre obras, RDOs, alertas e saúde "
    "contratual usando dados reais via tool calling.",
    response_model=ChatResponse,
    responses={
        200: {"description": "Resposta do agente"},
        503: {"description": "IA indisponível"},
    },
)
async def chat(
    dados: ChatRequest,
    usuario_atual: dict = Depends(get_usuario_atual),
    ia: IAService = Depends(get_ia_service),
):
    historico = [m.model_dump() for m in dados.historico]
    resultado = await ia.agente_chat(dados.mensagem, usuario_atual, historico)
    return ChatResponse(**resultado)

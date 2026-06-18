"""Endpoints de obras, vínculos, dashboard, alertas, evolução visual e dossiê."""

import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import (
    get_alerta_service,
    get_ia_service,
    get_obra_service,
    get_pdf_service,
    get_usuario_atual,
    requer_acesso_obra,
    requer_admin,
    requer_perfil_obra,
)
from app.api.v1.schemas.alerta import AlertaResponse
from app.api.v1.schemas.assinatura import DossieRequest
from app.api.v1.schemas.obra import (
    DashboardResponse,
    EvolucaoVisualResponse,
    ObraCreate,
    ObraResponse,
    ObraUpdate,
    ObraUsuarioCreate,
    ObraUsuarioResponse,
    ObraUsuarioUpdate,
    PermissoesExtrasUpdate,
)
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.services.alerta_service import AlertaService
from app.services.ia import IAService
from app.services.obra_service import ObraService
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/obras", tags=["obras"])

_PERFIS_GESTAO = (PerfilUsuario.FISCAL_SUAPE,)


@router.get(
    "/",
    summary="Listar obras acessíveis",
    description="Lista as obras que o usuário autenticado pode acessar (admin vê todas).",
    response_model=list[ObraResponse],
    responses={200: {"description": "Lista de obras"}},
)
async def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    usuario_atual: dict = Depends(get_usuario_atual),
    service: ObraService = Depends(get_obra_service),
):
    return await service.listar_acessiveis(usuario_atual, skip=skip, limit=limit)


@router.post(
    "/",
    summary="Criar obra",
    description="Cria uma nova obra e vincula automaticamente os fiscais informados. "
    "Restrito a administradores.",
    response_model=ObraResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Obra criada"},
        403: {"description": "Apenas admin"},
        422: {"description": "Referências inválidas (empresa/fiscal inexistente)"},
    },
)
async def criar(
    dados: ObraCreate,
    _admin: dict = Depends(requer_admin),
    service: ObraService = Depends(get_obra_service),
):
    return await service.criar(dados.model_dump())


@router.get(
    "/{id_obra}",
    summary="Detalhar obra",
    description="Retorna os dados de uma obra. Requer acesso à obra.",
    response_model=ObraResponse,
    responses={
        200: {"description": "Obra"},
        403: {"description": "Sem acesso"},
        404: {"description": "Não encontrada"},
    },
)
async def detalhar(
    id_obra: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: ObraService = Depends(get_obra_service),
):
    obra = await service.buscar(id_obra)
    await requer_acesso_obra(id_obra, usuario_atual)
    return obra


@router.patch(
    "/{id_obra}",
    summary="Atualizar obra",
    description="Atualiza os dados de uma obra. Restrito a administradores.",
    response_model=ObraResponse,
    responses={
        200: {"description": "Atualizada"},
        403: {"description": "Apenas admin"},
        404: {"description": "Não encontrada"},
    },
)
async def atualizar(
    id_obra: str,
    dados: ObraUpdate,
    _admin: dict = Depends(requer_admin),
    service: ObraService = Depends(get_obra_service),
):
    return await service.atualizar(id_obra, dados.model_dump(exclude_unset=True))


# ---- Vínculos Obra-Usuário ----


@router.get(
    "/{id_obra}/usuarios",
    summary="Listar usuários da obra",
    description="Lista os vínculos usuário-obra. Requer acesso à obra.",
    response_model=list[ObraUsuarioResponse],
    responses={200: {"description": "Lista de vínculos"}, 403: {"description": "Sem acesso"}},
)
async def listar_usuarios(
    id_obra: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: ObraService = Depends(get_obra_service),
):
    await requer_acesso_obra(id_obra, usuario_atual)
    return await service.listar_usuarios(id_obra)


@router.post(
    "/{id_obra}/usuarios",
    summary="Vincular usuário à obra",
    description="Vincula um usuário à obra com um perfil. Restrito a administradores.",
    response_model=ObraUsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Vínculo criado"},
        403: {"description": "Apenas admin"},
        404: {"description": "Obra ou usuário não encontrado"},
        409: {"description": "Usuário já vinculado"},
    },
)
async def vincular_usuario(
    id_obra: str,
    dados: ObraUsuarioCreate,
    _admin: dict = Depends(requer_admin),
    service: ObraService = Depends(get_obra_service),
):
    return await service.vincular_usuario(
        id_obra, dados.id_usuario, dados.perfil, dados.permissoes_extras
    )


@router.patch(
    "/{id_obra}/usuarios/{id_usuario}",
    summary="Atualizar perfil na obra",
    description="Altera o perfil de um usuário em uma obra. Restrito a administradores.",
    response_model=ObraUsuarioResponse,
    responses={
        200: {"description": "Atualizado"},
        403: {"description": "Apenas admin"},
        404: {"description": "Vínculo não encontrado"},
    },
)
async def atualizar_perfil(
    id_obra: str,
    id_usuario: str,
    dados: ObraUsuarioUpdate,
    _admin: dict = Depends(requer_admin),
    service: ObraService = Depends(get_obra_service),
):
    return await service.atualizar_perfil(id_obra, id_usuario, dados.perfil)


@router.delete(
    "/{id_obra}/usuarios/{id_usuario}",
    summary="Desvincular usuário da obra",
    description="Remove o vínculo de um usuário com a obra. Restrito a administradores.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Desvinculado"},
        403: {"description": "Apenas admin"},
        404: {"description": "Vínculo não encontrado"},
    },
)
async def desvincular_usuario(
    id_obra: str,
    id_usuario: str,
    _admin: dict = Depends(requer_admin),
    service: ObraService = Depends(get_obra_service),
):
    await service.desvincular(id_obra, id_usuario)


@router.patch(
    "/{id_obra}/usuarios/{id_usuario}/permissoes",
    summary="Atualizar permissões temporárias",
    description="Concede/ajusta permissões temporárias granulares ao fiscal externo "
    "(pode_adicionar_info, pode_comentar, pode_enviar_suape, expira_em). Restrito a admins.",
    response_model=ObraUsuarioResponse,
    responses={
        200: {"description": "Permissões atualizadas"},
        403: {"description": "Apenas admin"},
        404: {"description": "Vínculo não encontrado"},
    },
)
async def atualizar_permissoes(
    id_obra: str,
    id_usuario: str,
    dados: PermissoesExtrasUpdate,
    _admin: dict = Depends(requer_admin),
    service: ObraService = Depends(get_obra_service),
):
    return await service.atualizar_permissoes(
        id_obra, id_usuario, dados.model_dump(exclude_unset=True)
    )


# ---- Dashboard e Alertas ----


@router.get(
    "/{id_obra}/dashboard",
    summary="Dashboard da obra",
    description="Indicadores da obra: total de RDOs, distribuição por status e prazo "
    "decorrido. Restrito a admin ou Fiscal SUAPE.",
    response_model=DashboardResponse,
    responses={
        200: {"description": "Indicadores"},
        403: {"description": "Sem permissão"},
        404: {"description": "Não encontrada"},
    },
)
async def dashboard(
    id_obra: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: ObraService = Depends(get_obra_service),
):
    await requer_perfil_obra(id_obra, usuario_atual, _PERFIS_GESTAO)
    return await service.dashboard(id_obra)


@router.get(
    "/{id_obra}/alertas",
    summary="Alertas da obra",
    description="Recalcula e lista os alertas da obra (prazo, saúde, não conformidade). "
    "Restrito a admin ou Fiscal SUAPE.",
    response_model=list[AlertaResponse],
    responses={
        200: {"description": "Lista de alertas"},
        403: {"description": "Sem permissão"},
        404: {"description": "Não encontrada"},
    },
)
async def alertas_da_obra(
    id_obra: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    obra_service: ObraService = Depends(get_obra_service),
    alerta_service: AlertaService = Depends(get_alerta_service),
):
    await obra_service.buscar(id_obra)
    await requer_perfil_obra(id_obra, usuario_atual, _PERFIS_GESTAO)
    await alerta_service.gerar_alertas_obra(id_obra)
    return await alerta_service.listar_por_obra(id_obra)


@router.get(
    "/{id_obra}/evolucao-visual",
    summary="Evolução Visual da Obra por GPS",
    description="Agrupa fotos tiradas num raio de X metros de um ponto geográfico e retorna a "
    "linha do tempo visual do avanço físico daquele trecho da obra. Restrito a Admin ou "
    "Fiscal SUAPE.",
    response_model=EvolucaoVisualResponse,
    responses={
        200: {"description": "Linha do tempo visual"},
        403: {"description": "Acesso restrito a admin e fiscal SUAPE"},
        404: {"description": "Obra não encontrada"},
    },
)
async def evolucao_visual(
    id_obra: str,
    lat: float = Query(..., description="Latitude do ponto de referência"),
    lon: float = Query(..., description="Longitude do ponto de referência"),
    raio_metros: int = Query(50, ge=1, le=5000),
    data_inicio: Optional[datetime] = Query(None),
    data_fim: Optional[datetime] = Query(None),
    usuario_atual: dict = Depends(get_usuario_atual),
    ia_service: IAService = Depends(get_ia_service),
):
    await requer_perfil_obra(id_obra, usuario_atual, _PERFIS_GESTAO)
    return await ia_service.evolucao_visual(
        id_obra, lat, lon, raio_metros, data_inicio, data_fim
    )


@router.post(
    "/{id_obra}/dossie",
    summary="Dossiê Executivo da Obra (IA + PDF)",
    description="Gera um documento executivo consolidado da obra, com resumo narrativo por IA, "
    "indicadores, linha do tempo, análise de restrições e registro fotográfico. Restrito a "
    "Admin ou Fiscal SUAPE.",
    responses={
        200: {"description": "Dossiê gerado", "content": {"application/pdf": {}}},
        403: {"description": "Acesso restrito a admin e fiscal SUAPE"},
        404: {"description": "Obra não encontrada"},
    },
)
async def dossie(
    id_obra: str,
    dados: DossieRequest,
    usuario_atual: dict = Depends(get_usuario_atual),
    obra_service: ObraService = Depends(get_obra_service),
    pdf_service: PDFService = Depends(get_pdf_service),
):
    obra = await obra_service.buscar(id_obra)
    await requer_perfil_obra(id_obra, usuario_atual, _PERFIS_GESTAO)
    pdf = await pdf_service.gerar_dossie(id_obra, dados.data_inicio, dados.data_fim)
    contrato = str(obra.get("numero_contrato") or id_obra).replace("/", "-")
    nome = f"Dossie-Obra-{contrato}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )

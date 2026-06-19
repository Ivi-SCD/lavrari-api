"""Endpoints de RDOs: CRUD, versões e transições de workflow."""

import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import (
    get_assinatura_service,
    get_pdf_service,
    get_rdo_service,
    get_usuario_atual,
    get_workflow_service,
    requer_acesso_obra,
    requer_perfil_obra,
    requer_permissao_extra,
)
from app.api.v1.schemas.assinatura import AssinarRequest, AssinaturaResponse
from app.api.v1.schemas.rdo import (
    JustificativaRequest,
    MotivoRequest,
    RDOCreate,
    RDOResponse,
    RDOUpdate,
    RdoVersaoResponse,
)
from app.core.exceptions import PermissionDeniedError
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.services.assinatura_service import AssinaturaService
from app.services.pdf_service import PDFService
from app.services.rdo_service import RDOService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/rdos", tags=["rdos"])

_PERFIS_GESTAO = (PerfilUsuario.FISCAL_SUAPE,)


async def _ids_obras_do_usuario(usuario: dict) -> list[str]:
    vinculos = await ObraUsuarioRepository().listar_por_usuario(usuario["id_usuario"])
    return [v["id_obra"] for v in vinculos]


@router.get(
    "/",
    summary="Listar RDOs",
    description="Lista RDOs com filtros opcionais (id_obra, status, data_inicio, data_fim). "
    "Usuários não-admin só veem RDOs de obras às quais têm acesso.",
    response_model=list[RDOResponse],
    responses={200: {"description": "Lista de RDOs"}},
)
async def listar(
    id_obra: Optional[str] = Query(None),
    status_rdo: Optional[StatusRDO] = Query(None, alias="status"),
    data_inicio: Optional[datetime] = Query(None),
    data_fim: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    filtros: dict = {}
    if status_rdo:
        filtros["status"] = status_rdo.value
    if data_inicio or data_fim:
        intervalo: dict = {}
        if data_inicio:
            intervalo["$gte"] = data_inicio
        if data_fim:
            intervalo["$lte"] = data_fim
        filtros["data_relatorio"] = intervalo

    if usuario_atual.get("is_admin"):
        if id_obra:
            filtros["id_obra"] = id_obra
    else:
        permitidas = await _ids_obras_do_usuario(usuario_atual)
        if id_obra:
            if id_obra not in permitidas:
                raise PermissionDeniedError("Sem acesso a esta obra.")
            filtros["id_obra"] = id_obra
        else:
            if not permitidas:
                return []
            filtros["id_obra"] = {"$in": permitidas}

    return await service.listar(filtros, skip=skip, limit=limit)


@router.post(
    "/",
    summary="Criar RDO",
    description="Cria um RDO em status RASCUNHO. O clima é pré-preenchido via API de clima "
    "se a obra tiver coordenadas. Restrito a Fornecedores e Admins da obra.",
    response_model=RDOResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "RDO criado"},
        403: {"description": "Sem permissão para criar RDO nesta obra"},
        404: {"description": "Obra não encontrada"},
        422: {"description": "Dados inválidos"},
    },
)
async def criar(
    dados: RDOCreate,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    await requer_perfil_obra(dados.id_obra, usuario_atual, (PerfilUsuario.FORNECEDOR,))
    return await service.criar(dados.model_dump(), usuario_atual)


@router.get(
    "/{id_rdo}",
    summary="Detalhar RDO",
    description="Retorna um RDO específico. Requer acesso à obra do RDO.",
    response_model=RDOResponse,
    responses={
        200: {"description": "RDO"},
        403: {"description": "Sem acesso"},
        404: {"description": "Não encontrado"},
    },
)
async def detalhar(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    rdo = await service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    return rdo


@router.patch(
    "/{id_rdo}",
    summary="Editar RDO",
    description="Edita os campos de um RDO em RASCUNHO. Permitido a Fornecedor, Admin ou "
    "Fiscal Externo com permissão temporária 'pode_adicionar_info'.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Atualizado"},
        403: {"description": "Sem permissão"},
        404: {"description": "Não encontrado"},
        409: {"description": "RDO não está em RASCUNHO"},
    },
)
async def editar(
    id_rdo: str,
    dados: RDOUpdate,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    rdo = await service.buscar(id_rdo)
    id_obra = rdo["id_obra"]
    autorizado = usuario_atual.get("is_admin")
    if not autorizado:
        vinculo = await ObraUsuarioRepository().buscar_por_obra_e_usuario(
            id_obra, usuario_atual["id_usuario"]
        )
        perfil = vinculo["perfil"] if vinculo else None
        if perfil == PerfilUsuario.FORNECEDOR.value:
            autorizado = True
        elif perfil == PerfilUsuario.FISCAL_EXTERNO.value:
            autorizado = await requer_permissao_extra(
                id_obra, usuario_atual, "pode_adicionar_info"
            )
    if not autorizado:
        raise PermissionDeniedError("Sem permissão para editar este RDO.")
    return await service.atualizar(id_rdo, dados.model_dump(exclude_unset=True), usuario_atual)


@router.delete(
    "/{id_rdo}",
    summary="Excluir RDO",
    description="Exclui um RDO em RASCUNHO. Restrito a Admin ou Fiscal SUAPE.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Excluído"},
        403: {"description": "Sem permissão"},
        404: {"description": "Não encontrado"},
        409: {"description": "RDO não está em RASCUNHO"},
    },
)
async def excluir(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    rdo = await service.buscar(id_rdo)
    await requer_perfil_obra(rdo["id_obra"], usuario_atual, _PERFIS_GESTAO)
    await service.deletar(id_rdo)


# ---- Versões ----


@router.get(
    "/{id_rdo}/versoes",
    summary="Histórico de versões",
    description="Lista o histórico imutável de versões (snapshots) do RDO.",
    response_model=list[RdoVersaoResponse],
    responses={200: {"description": "Versões"}, 404: {"description": "Não encontrado"}},
)
async def listar_versoes(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    rdo = await service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    return await service.listar_versoes(id_rdo)


@router.get(
    "/{id_rdo}/versoes/{versao}",
    summary="Snapshot de versão",
    description="Retorna o snapshot completo de uma versão específica do RDO.",
    response_model=RdoVersaoResponse,
    responses={200: {"description": "Versão"}, 404: {"description": "Não encontrada"}},
)
async def detalhar_versao(
    id_rdo: str,
    versao: int,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
):
    rdo = await service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    return await service.buscar_versao(id_rdo, versao)


@router.get(
    "/{id_rdo}/versoes/{versao}/pdf",
    summary="PDF imutável de uma versão",
    description="Reproduz, na íntegra, o documento PDF daquela versão a partir do snapshot "
    "congelado (obra, responsáveis, ART e logos como estavam naquele momento). Alterações "
    "posteriores na obra não afetam este documento. Requer acesso à obra.",
    responses={
        200: {"description": "PDF da versão", "content": {"application/pdf": {}}},
        404: {"description": "Versão não encontrada"},
    },
)
async def pdf_versao(
    id_rdo: str,
    versao: int,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: RDOService = Depends(get_rdo_service),
    pdf_service: PDFService = Depends(get_pdf_service),
):
    rdo = await service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    versao_doc = await service.buscar_versao(id_rdo, versao)
    pdf, _ = await pdf_service.gerar_pdf_de_snapshot(versao_doc["snapshot"])
    nome = f"RDO-{rdo.get('numero_registro')}-v{versao}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ---- Transições de workflow ----


@router.post(
    "/{id_rdo}/submeter",
    summary="Submeter RDO para revisão",
    description="Envia o RDO (RASCUNHO) para revisão — Fiscal Externo se configurado, "
    "senão Fiscal SUAPE. Restrito a Fornecedor/Admin (ou Fiscal Externo autorizado).",
    response_model=RDOResponse,
    responses={
        200: {"description": "Submetido"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def submeter(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.submeter_rdo(id_rdo, usuario_atual)


@router.post(
    "/{id_rdo}/aprovar-externo",
    summary="Aprovar (Fiscal Externo)",
    description="Aprovação do Fiscal Externo, encaminhando o RDO ao Fiscal SUAPE.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Aprovado"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def aprovar_externo(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.aprovar_externo(id_rdo, usuario_atual)


@router.post(
    "/{id_rdo}/reprovar-externo",
    summary="Reprovar (Fiscal Externo)",
    description="Reprovação do Fiscal Externo. O motivo é salvo como comentário e o RDO "
    "retorna a RASCUNHO.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Reprovado"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def reprovar_externo(
    id_rdo: str,
    dados: MotivoRequest,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.reprovar_externo(id_rdo, usuario_atual, dados.motivo)


@router.post(
    "/{id_rdo}/aprovar-suape",
    summary="Aprovar (Fiscal SUAPE)",
    description="Aprovação final do Fiscal SUAPE. O RDO passa a APROVADO e é BLOQUEADO "
    "automaticamente.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Aprovado e bloqueado"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def aprovar_suape(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.aprovar_suape(id_rdo, usuario_atual)


@router.post(
    "/{id_rdo}/reprovar-suape",
    summary="Reprovar (Fiscal SUAPE)",
    description="Reprovação do Fiscal SUAPE. O motivo é salvo como comentário e o RDO "
    "retorna a RASCUNHO.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Reprovado"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def reprovar_suape(
    id_rdo: str,
    dados: MotivoRequest,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.reprovar_suape(id_rdo, usuario_atual, dados.motivo)


@router.post(
    "/{id_rdo}/reabrir",
    summary="Reabrir RDO",
    description="Reabre um RDO BLOQUEADO ou FINALIZADO, retornando a RASCUNHO. Requer "
    "justificativa obrigatória. Restrito a Admin ou Fiscal SUAPE.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Reaberto"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def reabrir(
    id_rdo: str,
    dados: JustificativaRequest,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.reabrir_rdo(id_rdo, usuario_atual, dados.justificativa)


@router.post(
    "/{id_rdo}/finalizar",
    summary="Finalizar RDO",
    description="Finaliza um RDO BLOQUEADO (MVP: sem coleta de assinaturas). Restrito a "
    "administradores.",
    response_model=RDOResponse,
    responses={
        200: {"description": "Finalizado"},
        403: {"description": "Sem permissão"},
        409: {"description": "Estado inválido"},
    },
)
async def finalizar(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.finalizar_rdo(id_rdo, usuario_atual)


# ---- PDF e Assinatura eletrônica ----


@router.get(
    "/{id_rdo}/pdf",
    summary="Gerar PDF do RDO",
    description="Gera o PDF do RDO no formato DNIT 097/2025 e retorna o arquivo para "
    "download. RDOs fora de BLOQUEADO/FINALIZADO recebem marca d'água 'NÃO OFICIAL'.",
    responses={
        200: {"description": "PDF gerado", "content": {"application/pdf": {}}},
        403: {"description": "Sem acesso ao RDO"},
        404: {"description": "RDO não encontrado"},
    },
)
async def gerar_pdf(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    pdf_service: PDFService = Depends(get_pdf_service),
    rdo_service: RDOService = Depends(get_rdo_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    pdf, _ = await pdf_service.gerar_pdf(id_rdo)
    nome = f"RDO-{rdo.get('numero_registro')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.post(
    "/{id_rdo}/assinar",
    summary="Assinar RDO eletronicamente",
    description="Registra aceite eletrônico auditável do RDO. Requer senha do usuário para "
    "confirmar identidade. Gera PDF, calcula SHA-256 e armazena no COS. Disponível apenas "
    "para RDOs em status BLOQUEADO ou FINALIZADO.",
    response_model=AssinaturaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Assinatura registrada"},
        400: {"description": "Usuário já assinou este RDO"},
        401: {"description": "Senha incorreta"},
        403: {"description": "Sem acesso ou RDO não está em status assinável"},
        404: {"description": "RDO não encontrado"},
    },
)
async def assinar(
    id_rdo: str,
    dados: AssinarRequest,
    request: Request,
    usuario_atual: dict = Depends(get_usuario_atual),
    assinatura_service: AssinaturaService = Depends(get_assinatura_service),
    rdo_service: RDOService = Depends(get_rdo_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    ip = request.client.host if request.client else None
    return await assinatura_service.assinar(
        id_rdo, usuario_atual, dados.senha, dados.papel, dados.cargo, ip
    )


@router.get(
    "/{id_rdo}/assinaturas",
    summary="Listar assinaturas do RDO",
    description="Lista todas as assinaturas eletrônicas registradas para o RDO.",
    response_model=list[AssinaturaResponse],
    responses={
        200: {"description": "Lista de assinaturas"},
        403: {"description": "Sem acesso"},
        404: {"description": "RDO não encontrado"},
    },
)
async def listar_assinaturas(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    assinatura_service: AssinaturaService = Depends(get_assinatura_service),
    rdo_service: RDOService = Depends(get_rdo_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    return await assinatura_service.listar_por_rdo(id_rdo)

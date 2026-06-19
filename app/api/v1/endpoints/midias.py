"""Endpoints de mídias (fotos georreferenciadas) de RDO."""

from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)

from app.api.v1.deps import (
    get_midia_service,
    get_rdo_service,
    get_usuario_atual,
    requer_acesso_obra,
    requer_permissao_extra,
)
from app.api.v1.schemas.midia import MidiaResponse
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.services.midia_service import MidiaService
from app.services.rdo_service import RDOService

router = APIRouter(prefix="/rdos/{id_rdo}/midias", tags=["midias"])

_TIPOS_IMAGEM = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


async def _pode_contribuir(id_obra: str, usuario: dict) -> bool:
    if usuario.get("is_admin"):
        return True
    vinculo = await ObraUsuarioRepository().buscar_por_obra_e_usuario(
        id_obra, usuario["id_usuario"]
    )
    perfil = vinculo["perfil"] if vinculo else None
    if perfil == PerfilUsuario.FORNECEDOR.value:
        return True
    if perfil == PerfilUsuario.FISCAL_EXTERNO.value:
        return await requer_permissao_extra(id_obra, usuario, "pode_adicionar_info")
    return False


@router.get(
    "/",
    summary="Listar fotos do RDO",
    description="Lista as fotos ativas (não deletadas) do RDO. Requer acesso à obra.",
    response_model=list[MidiaResponse],
    responses={200: {"description": "Lista de fotos"}, 404: {"description": "RDO não encontrado"}},
)
async def listar(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    rdo_service: RDOService = Depends(get_rdo_service),
    service: MidiaService = Depends(get_midia_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    return await service.listar(id_rdo)


@router.post(
    "/",
    summary="Upload de foto",
    description="Envia uma foto georreferenciada (latitude/longitude obrigatórios, não "
    "podem ser 0,0). A análise de IA é executada em segundo plano após o upload.",
    response_model=MidiaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Foto enviada"},
        403: {"description": "Sem permissão"},
        404: {"description": "RDO não encontrado"},
        422: {"description": "Arquivo ou coordenadas inválidos"},
    },
)
async def upload(
    id_rdo: str,
    background_tasks: BackgroundTasks,
    arquivo: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    data_hora_captura: datetime = Form(...),
    usuario_atual: dict = Depends(get_usuario_atual),
    rdo_service: RDOService = Depends(get_rdo_service),
    service: MidiaService = Depends(get_midia_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    if not await _pode_contribuir(rdo["id_obra"], usuario_atual):
        raise PermissionDeniedError("Sem permissão para enviar fotos neste RDO.")
    if arquivo.content_type not in _TIPOS_IMAGEM:
        raise ValidationError("Formato de imagem não suportado.")

    conteudo = await arquivo.read()
    midia = await service.upload(
        id_rdo,
        conteudo,
        arquivo.content_type or "image/jpeg",
        latitude,
        longitude,
        data_hora_captura,
        usuario_atual,
    )
    background_tasks.add_task(
        service.processar_em_background,
        midia["id_midia"],
        midia["storage_url"],
        latitude,
        longitude,
    )
    return midia


@router.delete(
    "/{id_midia}",
    summary="Remover foto",
    description="Remove (soft delete) uma foto do RDO. Permitido apenas com o RDO em "
    "RASCUNHO.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Removida"},
        403: {"description": "Sem permissão"},
        404: {"description": "Não encontrada"},
        409: {"description": "RDO não está em RASCUNHO"},
    },
)
async def remover(
    id_rdo: str,
    id_midia: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    rdo_service: RDOService = Depends(get_rdo_service),
    service: MidiaService = Depends(get_midia_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    if not await _pode_contribuir(rdo["id_obra"], usuario_atual):
        raise PermissionDeniedError("Sem permissão para remover fotos neste RDO.")
    await service.deletar(id_rdo, id_midia)

"""Endpoints de comentários de RDO."""

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import (
    get_comentario_service,
    get_rdo_service,
    get_usuario_atual,
    requer_acesso_obra,
    requer_permissao_extra,
)
from app.api.v1.schemas.comentario import ComentarioCreate, ComentarioResponse
from app.core.exceptions import PermissionDeniedError
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.services.comentario_service import ComentarioService
from app.services.rdo_service import RDOService

router = APIRouter(prefix="/rdos/{id_rdo}/comentarios", tags=["comentarios"])

# Perfis cujo comentário é sempre permitido (além de admin).
_PERFIS_COMENTARIO = {
    PerfilUsuario.FISCAL_SUAPE.value,
    PerfilUsuario.FORNECEDOR.value,
}


@router.get(
    "/",
    summary="Listar comentários",
    description="Lista os comentários do RDO em ordem cronológica. Requer acesso à obra.",
    response_model=list[ComentarioResponse],
    responses={200: {"description": "Comentários"}, 404: {"description": "RDO não encontrado"}},
)
async def listar(
    id_rdo: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    rdo_service: RDOService = Depends(get_rdo_service),
    service: ComentarioService = Depends(get_comentario_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    await requer_acesso_obra(rdo["id_obra"], usuario_atual)
    return await service.listar(id_rdo)


@router.post(
    "/",
    summary="Adicionar comentário",
    description="Adiciona um comentário ao RDO. Admin, Fiscal SUAPE e Fornecedor sempre "
    "podem; Fiscal Externo requer a permissão temporária 'pode_comentar'.",
    response_model=ComentarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Comentário criado"},
        403: {"description": "Sem permissão"},
        404: {"description": "RDO não encontrado"},
    },
)
async def adicionar(
    id_rdo: str,
    dados: ComentarioCreate,
    usuario_atual: dict = Depends(get_usuario_atual),
    rdo_service: RDOService = Depends(get_rdo_service),
    service: ComentarioService = Depends(get_comentario_service),
):
    rdo = await rdo_service.buscar(id_rdo)
    id_obra = rdo["id_obra"]
    autorizado = usuario_atual.get("is_admin")
    if not autorizado:
        vinculo = await ObraUsuarioRepository().buscar_por_obra_e_usuario(
            id_obra, usuario_atual["id_usuario"]
        )
        perfil = vinculo["perfil"] if vinculo else None
        if perfil in _PERFIS_COMENTARIO:
            autorizado = True
        elif perfil == PerfilUsuario.FISCAL_EXTERNO.value:
            autorizado = await requer_permissao_extra(id_obra, usuario_atual, "pode_comentar")
    if not autorizado:
        raise PermissionDeniedError("Sem permissão para comentar neste RDO.")
    return await service.adicionar(id_rdo, usuario_atual["id_usuario"], dados.conteudo, dados.tipo)

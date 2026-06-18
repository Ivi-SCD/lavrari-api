"""Endpoints de alertas."""

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_alerta_service, get_usuario_atual
from app.api.v1.schemas.alerta import AlertaResponse
from app.core.exceptions import PermissionDeniedError
from app.services.alerta_service import AlertaService

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get(
    "/",
    summary="Listar alertas do usuário",
    description="Lista os alertas das obras acessíveis ao usuário autenticado.",
    response_model=list[AlertaResponse],
    responses={200: {"description": "Alertas"}},
)
async def listar(
    usuario_atual: dict = Depends(get_usuario_atual),
    service: AlertaService = Depends(get_alerta_service),
):
    return await service.listar_do_usuario(usuario_atual)


@router.patch(
    "/{id_alerta}/lido",
    summary="Marcar alerta como lido",
    description="Marca um alerta como lido.",
    response_model=AlertaResponse,
    responses={200: {"description": "Atualizado"}, 404: {"description": "Não encontrado"}},
)
async def marcar_lido(
    id_alerta: str,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: AlertaService = Depends(get_alerta_service),
):
    if not usuario_atual.get("is_admin"):
        # Garante que o alerta pertence a uma obra acessível ao usuário.
        acessiveis = {a["id_alerta"] for a in await service.listar_do_usuario(usuario_atual)}
        if id_alerta not in acessiveis:
            raise PermissionDeniedError("Sem acesso a este alerta.")
    return await service.marcar_lido(id_alerta)

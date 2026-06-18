"""Endpoints administrativos (apenas administradores globais)."""

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_dashboard_service, requer_admin
from app.api.v1.schemas.dashboard import AdminDashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/dashboard",
    summary="Dashboard administrativo (métricas globais)",
    description="Consolida indicadores de todo o sistema — OS/RDO, aprovação, evidências e "
    "auditoria. Restrito a administradores globais.",
    response_model=AdminDashboardResponse,
    responses={
        200: {"description": "Métricas consolidadas"},
        403: {"description": "Ação restrita a administradores"},
    },
)
async def dashboard_admin(
    _admin: dict = Depends(requer_admin),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.metricas_globais()

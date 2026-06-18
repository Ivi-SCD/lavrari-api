"""Endpoints de empresas."""

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_empresa_service, get_usuario_atual, requer_admin
from app.api.v1.schemas.empresa import EmpresaCreate, EmpresaResponse, EmpresaUpdate
from app.services.empresa_service import EmpresaService

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get(
    "/",
    summary="Listar empresas",
    description="Lista as empresas cadastradas.",
    response_model=list[EmpresaResponse],
    responses={200: {"description": "Lista de empresas"}},
)
async def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _usuario: dict = Depends(get_usuario_atual),
    service: EmpresaService = Depends(get_empresa_service),
):
    return await service.listar(skip=skip, limit=limit)


@router.post(
    "/",
    summary="Criar empresa",
    description="Cadastra uma nova empresa. Restrito a administradores.",
    response_model=EmpresaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Empresa criada"},
        403: {"description": "Apenas admin"},
        409: {"description": "CNPJ já cadastrado"},
    },
)
async def criar(
    dados: EmpresaCreate,
    _admin: dict = Depends(requer_admin),
    service: EmpresaService = Depends(get_empresa_service),
):
    return await service.criar(dados.razao_social, dados.cnpj, dados.logo_url)


@router.get(
    "/{id_empresa}",
    summary="Detalhar empresa",
    description="Retorna os dados de uma empresa específica.",
    response_model=EmpresaResponse,
    responses={200: {"description": "Empresa"}, 404: {"description": "Não encontrada"}},
)
async def detalhar(
    id_empresa: str,
    _usuario: dict = Depends(get_usuario_atual),
    service: EmpresaService = Depends(get_empresa_service),
):
    return await service.buscar(id_empresa)


@router.patch(
    "/{id_empresa}",
    summary="Atualizar empresa",
    description="Atualiza os dados de uma empresa. Restrito a administradores.",
    response_model=EmpresaResponse,
    responses={
        200: {"description": "Atualizada"},
        403: {"description": "Apenas admin"},
        404: {"description": "Não encontrada"},
        409: {"description": "CNPJ já utilizado"},
    },
)
async def atualizar(
    id_empresa: str,
    dados: EmpresaUpdate,
    _admin: dict = Depends(requer_admin),
    service: EmpresaService = Depends(get_empresa_service),
):
    return await service.atualizar(id_empresa, dados.model_dump(exclude_unset=True))

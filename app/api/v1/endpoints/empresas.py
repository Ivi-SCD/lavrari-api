"""Endpoints de empresas."""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.v1.deps import get_empresa_service, get_usuario_atual, requer_admin
from app.api.v1.schemas.empresa import EmpresaCreate, EmpresaResponse, EmpresaUpdate
from app.core.exceptions import ValidationError
from app.services.empresa_service import EmpresaService

router = APIRouter(prefix="/empresas", tags=["empresas"])

_TIPOS_IMAGEM = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


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


@router.post(
    "/{id_empresa}/logo",
    summary="Enviar logo da empresa",
    description="Faz upload da logo da empresa. A imagem é redimensionada para a caixa "
    "padrão do card preservando a proporção (sem esticar). Restrito a administradores.",
    response_model=EmpresaResponse,
    responses={
        200: {"description": "Logo atualizada"},
        403: {"description": "Apenas admin"},
        404: {"description": "Empresa não encontrada"},
        422: {"description": "Arquivo de imagem inválido"},
    },
)
async def enviar_logo(
    id_empresa: str,
    arquivo: UploadFile = File(...),
    _admin: dict = Depends(requer_admin),
    service: EmpresaService = Depends(get_empresa_service),
):
    if arquivo.content_type not in _TIPOS_IMAGEM:
        raise ValidationError("Formato de imagem não suportado.")
    conteudo = await arquivo.read()
    return await service.atualizar_logo(id_empresa, conteudo)

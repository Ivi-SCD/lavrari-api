"""Endpoints de usuários."""

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_usuario_atual, get_usuario_service, requer_admin
from app.api.v1.schemas.auth import UsuarioResponse
from app.api.v1.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.core.exceptions import PermissionDeniedError
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get(
    "/",
    summary="Listar usuários",
    description="Lista todos os usuários do sistema. Restrito a administradores.",
    response_model=list[UsuarioResponse],
    responses={200: {"description": "Lista de usuários"}, 403: {"description": "Apenas admin"}},
)
async def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _admin: dict = Depends(requer_admin),
    service: UsuarioService = Depends(get_usuario_service),
):
    return await service.listar(skip=skip, limit=limit)


@router.post(
    "/",
    summary="Criar usuário",
    description="Cria um novo usuário. Restrito a administradores. Para criar outro admin, "
    "envie is_admin=true.",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Usuário criado"},
        403: {"description": "Apenas admin"},
        409: {"description": "E-mail já cadastrado"},
    },
)
async def criar(
    dados: UsuarioCreate,
    _admin: dict = Depends(requer_admin),
    service: UsuarioService = Depends(get_usuario_service),
):
    return await service.criar(dados.nome, dados.email, dados.senha, dados.is_admin)


@router.get(
    "/{id_usuario}",
    summary="Detalhar usuário",
    description="Retorna os dados de um usuário específico.",
    response_model=UsuarioResponse,
    responses={200: {"description": "Usuário"}, 404: {"description": "Não encontrado"}},
)
async def detalhar(
    id_usuario: str,
    _usuario: dict = Depends(get_usuario_atual),
    service: UsuarioService = Depends(get_usuario_service),
):
    return await service.buscar(id_usuario)


@router.patch(
    "/{id_usuario}",
    summary="Atualizar usuário",
    description="Atualiza nome e/ou e-mail. Permitido ao próprio usuário ou a um admin.",
    response_model=UsuarioResponse,
    responses={
        200: {"description": "Atualizado"},
        403: {"description": "Sem permissão"},
        404: {"description": "Não encontrado"},
        409: {"description": "E-mail já utilizado"},
    },
)
async def atualizar(
    id_usuario: str,
    dados: UsuarioUpdate,
    usuario_atual: dict = Depends(get_usuario_atual),
    service: UsuarioService = Depends(get_usuario_service),
):
    if not usuario_atual.get("is_admin") and usuario_atual["id_usuario"] != id_usuario:
        raise PermissionDeniedError("Você só pode atualizar seu próprio cadastro.")
    return await service.atualizar(id_usuario, dados.model_dump(exclude_unset=True))


@router.post(
    "/{id_usuario}/promover-admin",
    summary="Promover a administrador",
    description="Concede privilégio de administrador global ao usuário. Restrito a admins.",
    response_model=UsuarioResponse,
    responses={
        200: {"description": "Promovido"},
        403: {"description": "Apenas admin"},
        404: {"description": "Não encontrado"},
    },
)
async def promover_admin(
    id_usuario: str,
    _admin: dict = Depends(requer_admin),
    service: UsuarioService = Depends(get_usuario_service),
):
    return await service.promover_admin(id_usuario)

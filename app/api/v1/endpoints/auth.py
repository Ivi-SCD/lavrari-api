"""Endpoints de autenticação."""

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_auth_service, get_usuario_atual
from app.api.v1.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SetupRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.core.exceptions import ConflictError
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/setup",
    summary="Criar primeiro administrador",
    description="Cria o primeiro usuário administrador do sistema. Só funciona enquanto "
    "não existir nenhum admin no banco — após isso, retorna 409.",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Admin criado com sucesso"},
        409: {"description": "Já existe um administrador no sistema"},
        422: {"description": "Dados inválidos"},
    },
)
async def setup(dados: SetupRequest, auth: AuthService = Depends(get_auth_service)):
    if await UsuarioRepository().existe_admin():
        raise ConflictError("Já existe um administrador no sistema.")
    return await auth.criar_usuario(dados.nome, dados.email, dados.senha, is_admin=True)


@router.post(
    "/login",
    summary="Autenticar usuário",
    description="Valida e-mail e senha e retorna access_token + refresh_token.",
    response_model=TokenResponse,
    responses={
        200: {"description": "Autenticado com sucesso"},
        401: {"description": "Credenciais inválidas"},
    },
)
async def login(dados: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    access, refresh = await auth.autenticar(dados.email, dados.senha)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post(
    "/refresh",
    summary="Renovar access token",
    description="Gera um novo access_token a partir de um refresh_token válido.",
    response_model=AccessTokenResponse,
    responses={
        200: {"description": "Token renovado"},
        401: {"description": "Refresh token inválido, revogado ou expirado"},
    },
)
async def refresh(dados: RefreshRequest, auth: AuthService = Depends(get_auth_service)):
    access = await auth.renovar_token(dados.refresh_token)
    return AccessTokenResponse(access_token=access)


@router.post(
    "/logout",
    summary="Invalidar refresh token",
    description="Revoga o refresh_token informado, encerrando a sessão.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Logout efetuado"}},
)
async def logout(dados: LogoutRequest, auth: AuthService = Depends(get_auth_service)):
    await auth.invalidar_refresh_token(dados.refresh_token)


@router.get(
    "/me",
    summary="Dados do usuário autenticado",
    description="Retorna os dados do usuário associado ao access_token.",
    response_model=UsuarioResponse,
    responses={
        200: {"description": "Dados do usuário"},
        401: {"description": "Não autenticado"},
    },
)
async def me(usuario_atual: dict = Depends(get_usuario_atual)):
    return usuario_atual

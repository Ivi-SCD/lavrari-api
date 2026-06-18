"""Schemas de autenticação."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SetupRequest(BaseModel):
    nome: str = Field(..., min_length=2)
    email: EmailStr
    senha: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str


class UsuarioResponse(BaseModel):
    id_usuario: str
    nome: str
    email: str
    is_admin: bool
    criado_em: datetime
    atualizado_em: datetime

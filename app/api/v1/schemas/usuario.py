"""Schemas de Usuário."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2)
    email: EmailStr
    senha: str = Field(..., min_length=6)
    is_admin: bool = False


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2)
    email: Optional[EmailStr] = None

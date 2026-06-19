"""Schemas de Usuário."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.globals.enums.usuario.perfil_usuario import PerfilUsuario


class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2)
    email: EmailStr
    senha: str = Field(..., min_length=6)
    is_admin: bool = False


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2)
    email: Optional[EmailStr] = None


class VinculoUsuarioResponse(BaseModel):
    """Vínculo do usuário com uma obra: perfil e permissões temporárias (com expiração).

    Permite ao admin ver quem tem qual perfil/permissão em cada obra e por quanto tempo."""

    id_obra_usuario: str
    id_obra: str
    numero_contrato: Optional[str] = None
    objeto_contratual: Optional[str] = None
    perfil: PerfilUsuario
    permissoes_extras: dict
    permissoes_ativas: list[str] = Field(
        default_factory=list,
        description="Permissões extras atualmente válidas (respeitando expira_em)",
    )
    expira_em: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime

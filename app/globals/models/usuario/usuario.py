from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime, timezone


class Usuario(BaseModel):
    id_usuario: str = Field(..., description="ID do Usuário")
    nome: str = Field(..., description="Nome do Usuário")
    email: str = Field(..., description="E-mail do Usuário")
    senha_hash: str = Field(..., description="Hash da Senha do Usuário")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

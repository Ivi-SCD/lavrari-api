from pydantic import BaseModel, Field

from datetime import datetime, timezone

from app.globals.enums.usuario.perfil_usuario import PerfilUsuario


class ObraUsuario(BaseModel):
    id_obra_usuario: str = Field(..., description="ID do vínculo")
    id_obra: str = Field(..., description="ID da Obra")
    id_usuario: str = Field(..., description="ID do Usuário")
    perfil: PerfilUsuario = Field(..., description="Perfil do usuário nesta obra")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

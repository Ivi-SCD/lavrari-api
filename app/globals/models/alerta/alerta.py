from pydantic import BaseModel, Field

from datetime import datetime, timezone

from app.globals.enums.alerta.tipo_alerta import TipoAlerta, SeveridadeAlerta


class Alerta(BaseModel):
    id_alerta: str = Field(..., description="ID do Alerta")
    id_obra: str = Field(..., description="ID da Obra vinculada")
    tipo: TipoAlerta = Field(..., description="Tipo do Alerta")
    severidade: SeveridadeAlerta = Field(..., description="Severidade do Alerta")
    descricao: str = Field(..., description="Descrição gerada pela IA")
    lido: bool = Field(False, description="Alerta lido pelo fiscal/admin")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

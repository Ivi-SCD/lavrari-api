from pydantic import BaseModel, Field
from typing import Optional, List

from datetime import datetime, timezone

from app.globals.enums.rdo.status_rdo import StatusRDO

from app.globals.models.rdo.geral import (
    CondicaoClimatica,
    ItemPessoal,
    Equipamento,
    Servico,
    EventosRestricao,
)


class RDO(BaseModel):
    id_rdo: str = Field(..., description="ID do RDO")
    id_obra: str = Field(..., description="ID da Obra")
    numero_registro: int = Field(..., description="Número do Registro")
    data_relatorio: datetime = Field(..., description="Data do Relatório")
    status: StatusRDO = Field(..., description="Status do RDO")
    clima_manha: Optional[CondicaoClimatica] = Field(
        None, description="Condição Climática da Manhã"
    )
    clima_tarde: Optional[CondicaoClimatica] = Field(
        None, description="Condição Climática da Tarde"
    )
    pessoal_direto: Optional[List[ItemPessoal]] = Field(
        None, description="Lista de Pessoal Direto"
    )
    pessoal_indireto: Optional[List[ItemPessoal]] = Field(
        None, description="Lista de Pessoal Indireto"
    )
    equipamentos: Optional[List[Equipamento]] = Field(
        None, description="Lista de Equipamentos"
    )
    servicos: Optional[List[Servico]] = Field(None, description="Lista de Serviços")
    eventos_restricao: Optional[EventosRestricao] = Field(
        None, description="Eventos de Restrição"
    )

    resumo_dia: Optional[str] = Field(None, description="Resumo do Dia")
    ocorrencias: Optional[str] = Field(None, description="Ocorrências do Dia")
    aprovado_em: Optional[datetime] = Field(None, description="Data de Aprovação")
    criado_por: str = Field(..., description="Usuário que Criou o RDO")
    enviado_em: Optional[datetime] = Field(
        None, description="Data de Envio do RDO para revisão"
    )
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Criação",
    )
    atualizado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de Atualização",
    )

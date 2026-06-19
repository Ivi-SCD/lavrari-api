"""Schemas de Obra e vínculos Obra-Usuário."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.globals.enums.usuario.perfil_usuario import PerfilUsuario


class ResponsavelObraSchema(BaseModel):
    nome: str
    art: Optional[str] = None
    cargo: Optional[str] = None
    documento: Optional[str] = None


class ObraCreate(BaseModel):
    numero_contrato: str
    objeto_contratual: str
    tipologia: str
    local_descricao: str
    latitude_obra: Optional[float] = None
    longitude_obra: Optional[float] = None
    id_empresa_contratada: str
    id_empresa_supervisora: Optional[str] = None
    id_fiscal_suape: str
    art_fiscal_suape: Optional[str] = None
    id_fiscal_externo: Optional[str] = None
    art_fiscal_externo: Optional[str] = None
    responsaveis: List[ResponsavelObraSchema] = Field(default_factory=list)
    data_inicio_vigencia: datetime
    data_fim_vigencia: datetime
    data_inicio_execucao: datetime
    data_fim_execucao: datetime
    prazo_contratual_dias: int
    logo_suape_url: Optional[str] = None
    logo_contratada_url: Optional[str] = None


class ObraUpdate(BaseModel):
    numero_contrato: Optional[str] = None
    objeto_contratual: Optional[str] = None
    tipologia: Optional[str] = None
    local_descricao: Optional[str] = None
    latitude_obra: Optional[float] = None
    longitude_obra: Optional[float] = None
    id_empresa_contratada: Optional[str] = None
    id_empresa_supervisora: Optional[str] = None
    id_fiscal_suape: Optional[str] = None
    art_fiscal_suape: Optional[str] = None
    id_fiscal_externo: Optional[str] = None
    art_fiscal_externo: Optional[str] = None
    responsaveis: Optional[List[ResponsavelObraSchema]] = None
    data_inicio_vigencia: Optional[datetime] = None
    data_fim_vigencia: Optional[datetime] = None
    data_inicio_execucao: Optional[datetime] = None
    data_fim_execucao: Optional[datetime] = None
    prazo_contratual_dias: Optional[int] = None
    logo_suape_url: Optional[str] = None
    logo_contratada_url: Optional[str] = None


class ObraResponse(BaseModel):
    id_obra: str
    numero_contrato: str
    objeto_contratual: str
    tipologia: str
    local_descricao: str
    latitude_obra: Optional[float] = None
    longitude_obra: Optional[float] = None
    endereco: Optional[str] = None
    id_empresa_contratada: str
    id_empresa_supervisora: Optional[str] = None
    id_fiscal_suape: str
    art_fiscal_suape: Optional[str] = None
    id_fiscal_externo: Optional[str] = None
    art_fiscal_externo: Optional[str] = None
    responsaveis: List[ResponsavelObraSchema] = Field(default_factory=list)
    data_inicio_vigencia: datetime
    data_fim_vigencia: datetime
    data_inicio_execucao: datetime
    data_fim_execucao: datetime
    prazo_contratual_dias: int
    logo_suape_url: Optional[str] = None
    logo_contratada_url: Optional[str] = None


class ObraUsuarioCreate(BaseModel):
    id_usuario: str
    perfil: PerfilUsuario
    permissoes_extras: dict = Field(default_factory=dict)


class ObraUsuarioUpdate(BaseModel):
    perfil: PerfilUsuario


class PermissoesExtrasUpdate(BaseModel):
    pode_adicionar_info: Optional[bool] = None
    pode_comentar: Optional[bool] = None
    pode_enviar_suape: Optional[bool] = None
    expira_em: Optional[datetime] = None


class ObraUsuarioResponse(BaseModel):
    id_obra_usuario: str
    id_obra: str
    id_usuario: str
    nome: Optional[str] = None
    email: Optional[str] = None
    perfil: PerfilUsuario
    permissoes_extras: dict
    criado_em: datetime
    atualizado_em: datetime


class DashboardResponse(BaseModel):
    id_obra: str
    total_rdos: int
    rdos_por_status: dict
    dias_decorridos: int
    prazo_contratual_dias: int
    percentual_prazo: float
    total_alertas_abertos: int


# ---- Diferencial 2: Evolução Visual por GPS ----


class PontoGPS(BaseModel):
    lat: float
    lon: float


class EvolucaoVisualResponse(BaseModel):
    ponto: PontoGPS
    raio_metros: int
    total_fotos: int
    evolucao: List[dict[str, Any]]


# ---- Mapa 3D (Cesium): evidências georreferenciadas ----


class EvidenciaMapa(BaseModel):
    id_midia: str
    id_rdo: str
    numero_registro: Optional[int] = None
    data_relatorio: Optional[datetime] = None
    latitude: float
    longitude: float
    endereco: Optional[str] = None
    storage_url: str
    data_hora_captura: Optional[datetime] = None
    ai_analise: Optional[str] = None


class CentroMapa(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None


class MapaEvidenciasResponse(BaseModel):
    id_obra: str
    centro: CentroMapa
    total: int
    evidencias: List[EvidenciaMapa]

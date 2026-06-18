"""Schemas do dashboard administrativo."""

from typing import List

from pydantic import BaseModel


class ObrasMetricas(BaseModel):
    cadastradas: int
    os_cadastradas: int


class StatusDetalhe(BaseModel):
    status: str
    label: str
    quantidade: int


class RdosMetricas(BaseModel):
    cadastrados: int
    pendentes_correcao: int
    aprovados_finalizados: int
    bloqueados: int
    com_fiscal_externo: int
    com_restricao: int
    por_status: dict
    status_detalhado: List[StatusDetalhe]


class EvidenciasMetricas(BaseModel):
    cadastradas: int
    questionadas: int


class AssinaturasMetricas(BaseModel):
    aplicadas: int
    invalidas: int


class AuditoriaMetricas(BaseModel):
    eventos: int
    reaberturas: int


class ConformidadeMetricas(BaseModel):
    nao_conformidades_abertas: int
    eventos_com_restricao: int


class AdminDashboardResponse(BaseModel):
    obras: ObrasMetricas
    rdos: RdosMetricas
    evidencias: EvidenciasMetricas
    assinaturas: AssinaturasMetricas
    auditoria: AuditoriaMetricas
    conformidade: ConformidadeMetricas

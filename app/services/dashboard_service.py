"""Dashboard administrativo: métricas globais do sistema (apenas admin)."""

from app.globals.enums.alerta.tipo_alerta import TipoAlerta
from app.globals.enums.comentario.tipo_comentario import TipoComentario
from app.globals.enums.rdo.acao_versao import AcaoVersao
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.midia_repository import MidiaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_repository import RDORepository
from app.repositories.rdo_versao_repository import RdoVersaoRepository

# RDOs considerados concluídos no fluxo de aprovação.
_STATUS_CONCLUIDOS = {
    StatusRDO.APROVADO.value,
    StatusRDO.BLOQUEADO.value,
    StatusRDO.FINALIZADO.value,
}
# Status anteriores à aprovação — assinatura aqui indica reabertura (assinatura inválida).
_STATUS_PRE_APROVACAO = {
    StatusRDO.RASCUNHO.value,
    StatusRDO.REVISAO_EXTERNA.value,
    StatusRDO.REVISAO_SUAPE.value,
}

# Rótulos legíveis para o detalhamento de status no painel.
_STATUS_LABELS = {
    StatusRDO.RASCUNHO.value: "Rascunho",
    StatusRDO.REVISAO_EXTERNA.value: "Em Revisão Fiscal Externo",
    StatusRDO.REVISAO_SUAPE.value: "Em Revisão Fiscal SUAPE",
    StatusRDO.APROVADO.value: "Aprovado Fiscal SUAPE",
    StatusRDO.BLOQUEADO.value: "Bloqueado",
    StatusRDO.FINALIZADO.value: "Finalizado",
}


class DashboardService:
    def __init__(self):
        self.obra_repo = ObraRepository()
        self.rdo_repo = RDORepository()
        self.versao_repo = RdoVersaoRepository()
        self.midia_repo = MidiaRepository()
        self.assinatura_repo = AssinaturaRepository()
        self.alerta_repo = AlertaRepository()
        self.comentario_repo = ComentarioRepository()

    async def metricas_globais(self) -> dict:
        # --- Obras / OS ---
        total_obras = await self.obra_repo.contar({})

        obras_fiscal_externo = await self.obra_repo.listar(
            {"id_fiscal_externo": {"$ne": None}}, limit=10000
        )
        ids_obras_fe = [o["id_obra"] for o in obras_fiscal_externo]
        rdos_fiscal_externo = (
            len(await self.rdo_repo.ids_por_obras(ids_obras_fe)) if ids_obras_fe else 0
        )

        # --- RDOs ---
        por_status = await self.rdo_repo.contar_por_status_global()
        total_rdos = sum(por_status.values())
        concluidos = sum(por_status.get(s, 0) for s in _STATUS_CONCLUIDOS)
        pendentes = total_rdos - concluidos
        bloqueados = por_status.get(StatusRDO.BLOQUEADO.value, 0)
        com_restricao = await self.rdo_repo.contar_com_restricao()
        status_detalhado = [
            {"status": s, "label": lbl, "quantidade": por_status.get(s, 0)}
            for s, lbl in _STATUS_LABELS.items()
        ]

        # --- Evidências ---
        evidencias = await self.midia_repo.contar({"deletado_em": None})
        evidencias_questionadas = await self._contar_evidencias_questionadas()

        # --- Assinaturas ---
        assinaturas_aplicadas = await self.assinatura_repo.contar({})
        assinaturas_invalidas = await self._contar_assinaturas_invalidas()

        # --- Auditoria ---
        eventos_auditoria = await self.versao_repo.contar({})
        reaberturas = await self.versao_repo.contar({"acao": AcaoVersao.REABERTURA.value})

        # --- Conformidade ---
        nc_abertas = await self.alerta_repo.contar(
            {"tipo": TipoAlerta.PADRAO_NC.value, "lido": False}
        )

        return {
            "obras": {
                "cadastradas": total_obras,
                # OS não é modelada como entidade separada — no MVP cada obra equivale
                # a uma ordem de serviço; exposto como proxy para o painel.
                "os_cadastradas": total_obras,
            },
            "rdos": {
                "cadastrados": total_rdos,
                "pendentes_correcao": pendentes,
                "aprovados_finalizados": concluidos,
                "bloqueados": bloqueados,
                "com_fiscal_externo": rdos_fiscal_externo,
                "com_restricao": com_restricao,
                "por_status": por_status,
                "status_detalhado": status_detalhado,
            },
            "evidencias": {
                "cadastradas": evidencias,
                "questionadas": evidencias_questionadas,
            },
            "assinaturas": {
                "aplicadas": assinaturas_aplicadas,
                "invalidas": assinaturas_invalidas,
            },
            "auditoria": {
                "eventos": eventos_auditoria,
                "reaberturas": reaberturas,
            },
            "conformidade": {
                "nao_conformidades_abertas": nc_abertas,
                "eventos_com_restricao": com_restricao,
            },
        }

    async def _contar_evidencias_questionadas(self) -> int:
        """Evidências (fotos não deletadas) vinculadas a RDOs que receberam
        solicitação de correção — proxy para 'evidências que precisam revisão'."""
        cursor = self.comentario_repo.collection.find(
            {"tipo": TipoComentario.SOLICITACAO_CORRECAO.value}, {"id_rdo": 1, "_id": 0}
        )
        ids_rdo = {d["id_rdo"] async for d in cursor}
        if not ids_rdo:
            return 0
        return await self.midia_repo.contar(
            {"id_rdo": {"$in": list(ids_rdo)}, "deletado_em": None}
        )

    async def _contar_assinaturas_invalidas(self) -> int:
        """Assinatura é inválida quando o RDO assinado voltou a um status anterior
        à aprovação (reabertura após a assinatura)."""
        cursor = self.assinatura_repo.collection.find({}, {"id_rdo": 1, "_id": 0})
        ids_assinados = {d["id_rdo"] async for d in cursor}
        if not ids_assinados:
            return 0
        return await self.rdo_repo.contar(
            {"id_rdo": {"$in": list(ids_assinados)}, "status": {"$in": list(_STATUS_PRE_APROVACAO)}}
        )

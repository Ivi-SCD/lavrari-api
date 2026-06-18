"""Serviço de geração e gestão de alertas de obra."""

import logging
import uuid
from datetime import datetime, timezone

from app.core.exceptions import NotFoundError
from app.globals.enums.alerta.tipo_alerta import SeveridadeAlerta, TipoAlerta
from app.globals.models.alerta.alerta import Alerta
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.services.ia import IAService

logger = logging.getLogger(__name__)


class AlertaService:
    def __init__(self):
        self.repo = AlertaRepository()
        self.obra_repo = ObraRepository()
        self.obra_usuario_repo = ObraUsuarioRepository()
        self.ia = IAService()

    async def _persistir(self, id_obra: str, tipo: TipoAlerta, severidade: SeveridadeAlerta, descricao: str) -> dict:
        alerta = Alerta(
            id_alerta=str(uuid.uuid4()),
            id_obra=id_obra,
            tipo=tipo,
            severidade=severidade,
            descricao=descricao,
            lido=False,
        )
        return await self.repo.criar(alerta.model_dump())

    async def gerar_alertas_obra(self, id_obra: str) -> list[dict]:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            raise NotFoundError("Obra não encontrada.")

        novos: list[dict] = []

        # Prazo em risco (> 80% decorrido).
        inicio = obra.get("data_inicio_execucao")
        prazo = obra.get("prazo_contratual_dias") or 0
        if isinstance(inicio, datetime) and prazo:
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=timezone.utc)
            decorridos = max((datetime.now(timezone.utc) - inicio).days, 0)
            if decorridos / prazo > 0.8:
                if not await self.repo.existe_alerta_aberto(id_obra, TipoAlerta.PRAZO_EM_RISCO.value):
                    pct = round(decorridos / prazo * 100, 1)
                    novos.append(
                        await self._persistir(
                            id_obra,
                            TipoAlerta.PRAZO_EM_RISCO,
                            SeveridadeAlerta.ALTA,
                            f"{pct}% do prazo contratual decorrido ({decorridos}/{prazo} dias).",
                        )
                    )

        # Saúde crítica (score < 40).
        saude = await self.ia.calcular_saude_obra(id_obra)
        if saude["score"] < 40:
            if not await self.repo.existe_alerta_aberto(id_obra, TipoAlerta.SAUDE_CRITICA.value):
                novos.append(
                    await self._persistir(
                        id_obra,
                        TipoAlerta.SAUDE_CRITICA,
                        SeveridadeAlerta.CRITICA,
                        f"Score de saúde da obra em {saude['score']}/100 (crítico).",
                    )
                )

        # Padrões de não conformidade (PADRAO_NC) são gerados pelo endpoint dedicado
        # /ia/padroes-nc (Diferencial 3), que usa LLM e persiste os próprios alertas.

        return novos

    async def listar_por_obra(self, id_obra: str) -> list[dict]:
        return await self.repo.listar_por_obra(id_obra)

    async def listar_do_usuario(self, usuario: dict) -> list[dict]:
        if usuario.get("is_admin"):
            return await self.repo.listar({}, limit=1000, ordenar=[("criado_em", -1)])
        vinculos = await self.obra_usuario_repo.listar_por_usuario(usuario["id_usuario"])
        ids = [v["id_obra"] for v in vinculos]
        return await self.repo.listar_por_obras(ids) if ids else []

    async def marcar_lido(self, id_alerta: str) -> dict:
        alerta = await self.repo.buscar_por_id(id_alerta)
        if not alerta:
            raise NotFoundError("Alerta não encontrado.")
        await self.repo.marcar_lido(id_alerta)
        return await self.repo.buscar_por_id(id_alerta)

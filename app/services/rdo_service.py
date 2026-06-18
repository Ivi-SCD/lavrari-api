"""Serviço de RDOs (CRUD e criação com pré-preenchimento de clima)."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import NotFoundError, StateError
from app.globals.enums.rdo.acao_versao import AcaoVersao
from app.globals.enums.rdo.fonte_dado_rdo import FonteDado
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.globals.models.rdo.geral import CondicaoClimatica
from app.globals.models.rdo.rdo import RDO
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_repository import RDORepository
from app.services.clima_service import ClimaService
from app.services.versioning_service import VersioningService

logger = logging.getLogger(__name__)


class RDOService:
    def __init__(self):
        self.repo = RDORepository()
        self.obra_repo = ObraRepository()
        self.versioning = VersioningService()
        self.clima = ClimaService()

    async def buscar(self, id_rdo: str) -> dict:
        rdo = await self.repo.buscar_por_id(id_rdo)
        if not rdo:
            raise NotFoundError("RDO não encontrado.")
        return rdo

    async def listar(self, filtros: dict, skip: int = 0, limit: int = 100) -> list[dict]:
        return await self.repo.listar(
            filtros, skip=skip, limit=limit, ordenar=[("data_relatorio", -1)]
        )

    async def _clima_automatico(self, obra: dict) -> Optional[CondicaoClimatica]:
        lat, lon = obra.get("latitude_obra"), obra.get("longitude_obra")
        if lat is None or lon is None:
            return None
        try:
            dados = await self.clima.buscar_clima_atual(lat, lon)
            if not dados:
                return None
            return CondicaoClimatica(
                tempo=dados["descricao"],
                praticavel=dados["praticavel"],
                fonte=FonteDado.API_CLIMA,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao buscar clima automático: %s", exc)
            return None

    async def criar(self, dados: dict, usuario: dict) -> dict:
        obra = await self.obra_repo.buscar_por_id(dados["id_obra"])
        if not obra:
            raise NotFoundError("Obra não encontrada.")

        dados = dict(dados)
        if dados.get("clima_manha") is None or dados.get("clima_tarde") is None:
            clima_auto = await self._clima_automatico(obra)
            if clima_auto:
                if dados.get("clima_manha") is None:
                    dados["clima_manha"] = clima_auto.model_dump()
                if dados.get("clima_tarde") is None:
                    dados["clima_tarde"] = clima_auto.model_dump()

        rdo = RDO(
            id_rdo=str(uuid.uuid4()),
            numero_registro=await self.repo.proximo_numero_registro(dados["id_obra"]),
            status=StatusRDO.RASCUNHO,
            criado_por=usuario["id_usuario"],
            **dados,
        )
        criado = await self.repo.criar(rdo.model_dump())
        await self.versioning.criar_versao(criado, AcaoVersao.CRIACAO, usuario)
        return criado

    async def atualizar(self, id_rdo: str, dados: dict, usuario: dict) -> dict:
        rdo = await self.buscar(id_rdo)
        if rdo["status"] != StatusRDO.RASCUNHO.value:
            raise StateError("Apenas RDOs em RASCUNHO podem ser editados.")
        dados = {k: v for k, v in dados.items() if v is not None}
        atualizado = await self.repo.atualizar(id_rdo, dados)
        await self.versioning.criar_versao(atualizado, AcaoVersao.EDICAO, usuario)
        return atualizado

    async def deletar(self, id_rdo: str) -> None:
        rdo = await self.buscar(id_rdo)
        if rdo["status"] != StatusRDO.RASCUNHO.value:
            raise StateError("Apenas RDOs em RASCUNHO podem ser excluídos.")
        await self.repo.deletar(id_rdo)

    async def listar_versoes(self, id_rdo: str) -> list[dict]:
        await self.buscar(id_rdo)
        return await self.versioning.listar_versoes(id_rdo)

    async def buscar_versao(self, id_rdo: str, versao: int) -> dict:
        await self.buscar(id_rdo)
        encontrada = await self.versioning.buscar_versao(id_rdo, versao)
        if not encontrada:
            raise NotFoundError("Versão não encontrada.")
        return encontrada

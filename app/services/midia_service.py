"""Serviço de mídias (fotos georreferenciadas) de RDO."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.globals.enums.midia.tipo_midia import TipoMidia
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.globals.models.midia.midia import Midia
from app.repositories.midia_repository import MidiaRepository
from app.repositories.rdo_repository import RDORepository
from app.services.geocoding_service import GeocodingService
from app.services.ia import IAService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class MidiaService:
    def __init__(self):
        self.repo = MidiaRepository()
        self.rdo_repo = RDORepository()
        self.storage = StorageService()
        self.ia = IAService()
        self.geocoding = GeocodingService()

    async def listar(self, id_rdo: str) -> list[dict]:
        if not await self.rdo_repo.buscar_por_id(id_rdo):
            raise NotFoundError("RDO não encontrado.")
        return await self.repo.listar_por_rdo(id_rdo)

    @staticmethod
    def _validar_coordenadas(latitude: Optional[float], longitude: Optional[float]) -> None:
        if latitude is None or longitude is None:
            raise ValidationError("Latitude e longitude são obrigatórias.")
        if latitude == 0.0 and longitude == 0.0:
            raise ValidationError("Coordenadas (0,0) inválidas — GPS indisponível.")

    async def upload(
        self,
        id_rdo: str,
        arquivo_bytes: bytes,
        content_type: str,
        latitude: float,
        longitude: float,
        data_hora_captura: datetime,
        usuario: dict,
    ) -> dict:
        rdo = await self.rdo_repo.buscar_por_id(id_rdo)
        if not rdo:
            raise NotFoundError("RDO não encontrado.")
        self._validar_coordenadas(latitude, longitude)

        storage_url, storage_key = await self.storage.upload_foto(
            arquivo_bytes, id_rdo, content_type
        )

        midia = Midia(
            id_midia=str(uuid.uuid4()),
            id_rdo=id_rdo,
            tipo=TipoMidia.FOTO,
            storage_url=storage_url,
            latitude=latitude,
            longitude=longitude,
            data_hora_captura=data_hora_captura,
            criado_por=usuario["id_usuario"],
        )
        doc = midia.model_dump()
        doc["storage_key"] = storage_key
        return await self.repo.criar(doc)

    async def processar_em_background(
        self, id_midia: str, storage_url: str, latitude: float, longitude: float
    ) -> None:
        """Executado como BackgroundTask: análise de IA + geocodificação reversa do
        local da evidência, persistindo ambos sem bloquear o upload."""
        try:
            analise = await self.ia.analisar_imagem(storage_url)
            await self.repo.atualizar(id_midia, {"ai_analise": analise})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha na análise de IA da mídia %s: %s", id_midia, exc)

        try:
            endereco = await self.geocoding.reverso(latitude, longitude)
            if endereco:
                await self.repo.atualizar(id_midia, {"endereco": endereco})
        except Exception as exc:  # noqa: BLE001
            logger.info("Falha na geocodificação da mídia %s: %s", id_midia, exc)

    async def deletar(self, id_rdo: str, id_midia: str) -> None:
        rdo = await self.rdo_repo.buscar_por_id(id_rdo)
        if not rdo:
            raise NotFoundError("RDO não encontrado.")
        if rdo["status"] != StatusRDO.RASCUNHO.value:
            raise StateError("Fotos só podem ser removidas com o RDO em RASCUNHO.")
        midia = await self.repo.buscar_por_id(id_midia)
        if not midia or midia.get("deletado_em") is not None:
            raise NotFoundError("Mídia não encontrada.")
        await self.repo.soft_delete(id_midia)

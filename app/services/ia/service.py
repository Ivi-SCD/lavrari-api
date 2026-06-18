"""Fachada do serviço de IA — delega para os módulos especializados.

Mantém a interface pública usada pelos endpoints e demais serviços, enquanto a
implementação fica segregada por responsabilidade (analytics, insights, media,
agente e tools/).
"""

from datetime import datetime
from typing import Optional

from app.services.ia.agente import AgenteChatService
from app.services.ia.analytics import EvolucaoService, SaudeService
from app.services.ia.insights import (
    PadroesService,
    ResumoExecutivoService,
    SugestaoService,
)
from app.services.ia.media import MediaIAService


class IAService:
    def __init__(self):
        self._saude = SaudeService()
        self._evolucao = EvolucaoService()
        self._padroes = PadroesService()
        self._sugestao = SugestaoService()
        self._media = MediaIAService()
        self._resumo = ResumoExecutivoService()
        self._agente = AgenteChatService()

    async def transcrever_audio(
        self, audio_bytes: bytes, filename: str = "audio.m4a"
    ) -> str:
        return await self._media.transcrever(audio_bytes, filename)

    async def analisar_imagem(self, imagem_url: str) -> str:
        return await self._media.analisar_imagem(imagem_url)

    async def sugerir_texto_rdo(
        self, id_obra: str, data: datetime, historico_rdos: list[dict]
    ) -> dict:
        return await self._sugestao.sugerir(id_obra, data, historico_rdos)

    async def calcular_saude_obra(self, id_obra: str) -> dict:
        return await self._saude.calcular(id_obra)

    async def evolucao_visual(
        self,
        id_obra: str,
        lat: float,
        lon: float,
        raio_metros: int = 50,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> dict:
        return await self._evolucao.calcular(
            id_obra, lat, lon, raio_metros, data_inicio, data_fim
        )

    async def detectar_padroes_nc(self, id_obra: str) -> dict:
        return await self._padroes.detectar(id_obra)

    async def agente_chat(
        self, mensagem: str, usuario: dict, historico: Optional[list[dict]] = None
    ) -> dict:
        return await self._agente.responder(mensagem, usuario, historico)

    async def gerar_resumo_executivo(self, contexto: dict) -> str:
        return await self._resumo.gerar(contexto)

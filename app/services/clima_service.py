"""Serviço de clima via OpenWeatherMap."""

import logging
from typing import Optional

import httpx

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_CONDICOES_NAO_PRATICAVEIS = {"Rain", "Thunderstorm", "Drizzle", "Snow"}


class ClimaService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    async def buscar_clima_atual(self, latitude: float, longitude: float) -> Optional[dict]:
        if not settings.WEATHER_API_KEY:
            logger.info("WEATHER_API_KEY ausente — clima automático desativado.")
            return None
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": settings.WEATHER_API_KEY,
            "units": "metric",
            "lang": "pt_br",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            dados = resp.json()

        condicoes = dados.get("weather", [{}])
        principal = condicoes[0].get("main", "") if condicoes else ""
        descricao = condicoes[0].get("description", "") if condicoes else ""
        temperatura = dados.get("main", {}).get("temp")
        praticavel = principal not in _CONDICOES_NAO_PRATICAVEIS

        return {
            "temperatura": temperatura,
            "descricao": descricao or principal or "Indefinido",
            "praticavel": praticavel,
        }

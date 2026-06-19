"""Geocodificação reversa (coordenada → logradouro) via Nominatim/OpenStreetMap.

Best-effort: qualquer falha (timeout, rate-limit, indisponibilidade) retorna None
sem interromper o fluxo principal. O Nominatim exige um User-Agent identificável e
recomenda no máximo 1 requisição por segundo — uso pontual (cadastro de obra e
processamento de mídia em background) está dentro da política de uso justo.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GeocodingService:
    BASE_URL = "https://nominatim.openstreetmap.org/reverse"
    _USER_AGENT = "Lavrari-RDO/1.0 (https://suape.pe.gov.br)"

    @staticmethod
    def _coordenada_valida(lat: Optional[float], lon: Optional[float]) -> bool:
        if lat is None or lon is None:
            return False
        if lat == 0.0 and lon == 0.0:
            return False
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0

    @staticmethod
    def _montar_logradouro(addr: dict) -> Optional[str]:
        """Monta 'Rua/Avenida, bairro - cidade/UF' a partir do address do Nominatim."""
        via = (
            addr.get("road")
            or addr.get("pedestrian")
            or addr.get("footway")
            or addr.get("neighbourhood")
        )
        bairro = addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district")
        cidade = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village")
        uf = addr.get("state_code") or addr.get("state")

        partes: list[str] = []
        if via:
            partes.append(str(via))
        if bairro and bairro != via:
            partes.append(str(bairro))
        local = ", ".join(partes)
        municipio = " - ".join(p for p in [cidade, uf] if p)
        if local and municipio:
            return f"{local} - {municipio}"
        return local or municipio or None

    async def reverso(self, latitude: float, longitude: float) -> Optional[str]:
        if not self._coordenada_valida(latitude, longitude):
            return None
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "zoom": 18,
            "addressdetails": 1,
            "accept-language": "pt-BR",
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    self.BASE_URL, params=params, headers={"User-Agent": self._USER_AGENT}
                )
                resp.raise_for_status()
                dados = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.info("Geocodificação reversa indisponível (%s, %s): %s", latitude, longitude, exc)
            return None

        endereco = self._montar_logradouro(dados.get("address") or {})
        return endereco or dados.get("display_name")

"""Configuração de cliente (mapa 3D Cesium) e utilidades de geocodificação."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.v1.deps import get_usuario_atual
from app.core.config.settings import get_settings
from app.services.geocoding_service import GeocodingService

router = APIRouter(prefix="/config", tags=["config"])

settings = get_settings()


class ConfigClienteResponse(BaseModel):
    cesium_ion_access_token: str
    mapa_3d_habilitado: bool
    clima_habilitado: bool


class GeocodeReversoResponse(BaseModel):
    latitude: float
    longitude: float
    endereco: Optional[str] = None


@router.get(
    "/cliente",
    summary="Configuração do cliente (mapa 3D)",
    description="Retorna o token público do Cesium ion e flags de recursos para o frontend "
    "inicializar a visualização 3D do mapa.",
    response_model=ConfigClienteResponse,
)
async def config_cliente(_usuario: dict = Depends(get_usuario_atual)):
    token = settings.CESIUM_ION_ACCESS_TOKEN
    return ConfigClienteResponse(
        cesium_ion_access_token=token,
        mapa_3d_habilitado=bool(token),
        clima_habilitado=bool(settings.WEATHER_API_KEY),
    )


@router.get(
    "/geocode/reverso",
    summary="Geocodificação reversa (coordenada → logradouro)",
    description="Resolve o nome do logradouro a partir de uma coordenada — útil para exibir "
    "o local em tempo real no momento da captura da foto.",
    response_model=GeocodeReversoResponse,
)
async def geocode_reverso(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    _usuario: dict = Depends(get_usuario_atual),
):
    endereco = await GeocodingService().reverso(lat, lon)
    return GeocodeReversoResponse(latitude=lat, longitude=lon, endereco=endereco)

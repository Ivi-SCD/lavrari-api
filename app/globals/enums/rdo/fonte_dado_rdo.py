from enum import Enum


class FonteDado(str, Enum):
    MANUAL = "manual"
    TRANSCRICAO = "transcricao"
    API_CLIMA = "api_clima"

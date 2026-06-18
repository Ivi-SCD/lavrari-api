from enum import Enum


class TipoAlerta(str, Enum):
    SAUDE_CRITICA = "saude_critica"
    PADRAO_NC = "padrao_nc"
    PRAZO_EM_RISCO = "prazo_em_risco"


class SeveridadeAlerta(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

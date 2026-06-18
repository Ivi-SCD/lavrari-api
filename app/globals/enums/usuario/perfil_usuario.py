from enum import Enum


class PerfilUsuario(str, Enum):
    ADMINISTRADOR = "administrador"
    FISCAL_SUAPE = "fiscal_suape"
    FISCAL_EXTERNO = "fiscal_externo"
    FORNECEDOR = "fornecedor"
    CONSULTA = "consulta"

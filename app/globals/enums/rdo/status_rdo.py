from enum import Enum


class StatusRDO(str, Enum):
    RASCUNHO = "rascunho"
    REVISAO_EXTERNA = "revisao_externa"
    REVISAO_SUAPE = "revisao_suape"
    APROVADO = "aprovado"
    BLOQUEADO = "bloqueado"
    FINALIZADO = "finalizado"

from enum import Enum


class AcaoVersao(str, Enum):
    CRIACAO = "criacao"
    EDICAO = "edicao"
    ENVIO_REVISAO = "envio_revisao"
    APROVACAO_EXTERNA = "aprovacao_externa"
    REPROVACAO_EXTERNA = "reprovacao_externa"
    APROVACAO_SUAPE = "aprovacao_suape"
    REPROVACAO_SUAPE = "reprovacao_suape"
    REABERTURA = "reabertura"
    FINALIZACAO = "finalizacao"

from enum import Enum


class TipoComentario(str, Enum):
    COMENTARIO = "comentario"
    PARECER = "parecer"
    SOLICITACAO_CORRECAO = "solicitacao_correcao"
    AI_SUGESTAO = "ai_sugestao"

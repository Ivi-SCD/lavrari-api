"""Exceções de domínio mapeadas para respostas HTTP em main.py."""


class AppError(Exception):
    status_code = 400

    def __init__(self, mensagem: str):
        self.mensagem = mensagem
        super().__init__(mensagem)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PermissionDeniedError(AppError):
    status_code = 403


class ValidationError(AppError):
    status_code = 422


class StateError(AppError):
    """Transição de estado inválida na máquina de estados do RDO."""

    status_code = 409


class AuthError(AppError):
    status_code = 401


class ServiceUnavailableError(AppError):
    status_code = 503

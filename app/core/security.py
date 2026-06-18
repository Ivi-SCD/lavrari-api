"""Utilitários de segurança: hashing de senha e emissão/validação de JWT."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config.settings import get_settings

settings = get_settings()

_BCRYPT_MAX_BYTES = 72


def hash_senha(senha: str) -> str:
    senha_bytes = senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        senha_bytes = senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _criar_token(id_usuario: str, tipo: str, expira_em: datetime, extra: Optional[dict] = None) -> str:
    payload: dict[str, Any] = {
        "sub": id_usuario,
        "type": tipo,
        "jti": str(uuid.uuid4()),
        "exp": expira_em,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def criar_access_token(id_usuario: str, extra: Optional[dict] = None) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return _criar_token(id_usuario, "access", expira_em, extra)


def criar_refresh_token(id_usuario: str) -> tuple[str, datetime]:
    expira_em = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    return _criar_token(id_usuario, "refresh", expira_em), expira_em


def decodificar_token(token: str) -> dict:
    """Decodifica e valida um JWT. Lança JWTError se inválido/expirado."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "hash_senha",
    "verificar_senha",
    "criar_access_token",
    "criar_refresh_token",
    "decodificar_token",
    "JWTError",
]

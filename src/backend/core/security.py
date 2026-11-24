"""Seguridad: hash de contraseñas, JWT y dependencias de autorización."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from psycopg import Connection

from ..repositories import auth_repo
from .config import get_settings
from .database import get_db

INACTIVE_MESSAGE = "Usuario inactivo. Contacte al administrador"
INVALID_TOKEN_MESSAGE = "Token inválido o expirado"
INVALID_CREDENTIALS_MESSAGE = "Credenciales inválidas"
ADMIN_REQUIRED_MESSAGE = "Se requieren permisos de administrador"
GESTION_REQUIRED_MESSAGE = "Se requieren permisos de administrador o supervisor"
ROLES_GESTION = {"ADMIN", "SUPERVISOR"}

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Genera un hash bcrypt con costo 12 (prefijo ``$2b$12$``)."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Firma un JWT con el correo como ``sub`` y expiración configurable."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida la firma y vigencia del token."""
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_MESSAGE,
        ) from error


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    conn: Connection[Any] = Depends(get_db),
) -> dict[str, Any]:
    """Resuelve el usuario autenticado y bloquea cuentas inactivas."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    payload = decode_access_token(credentials.credentials)
    correo = payload.get("sub")
    if not correo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_MESSAGE,
        )

    usuario = auth_repo.obtener_usuario_por_correo(conn, correo)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_MESSAGE,
        )
    if not usuario.get("estado"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=INACTIVE_MESSAGE,
        )
    return usuario


def require_admin(
    usuario: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Permite el acceso solo al rol ``ADMIN``."""
    if str(usuario.get("rol", "")).strip().upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_REQUIRED_MESSAGE,
        )
    return usuario


def require_gestion(
    usuario: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Permite el acceso a los roles ``ADMIN`` y ``SUPERVISOR``."""
    rol = str(usuario.get("rol", "")).strip().upper()
    if rol not in ROLES_GESTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=GESTION_REQUIRED_MESSAGE,
        )
    return usuario

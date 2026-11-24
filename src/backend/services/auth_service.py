"""Reglas de negocio de autenticación."""

from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.security import (
    INACTIVE_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    create_access_token,
    verify_password,
)
from ..repositories import auth_repo


def login(
    conn: Connection[Any],
    correo: str,
    password: str,
) -> dict[str, Any]:
    """Valida credenciales y devuelve el token junto con los datos de sesión."""
    usuario = auth_repo.obtener_usuario_por_correo(conn, correo)

    if usuario is not None and not usuario.get("estado"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=INACTIVE_MESSAGE,
        )

    if usuario is None or not verify_password(password, usuario["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
        )

    token = create_access_token(
        usuario["correo"],
        {"id_usuario": usuario["id_usuario"], "rol": usuario["rol"]},
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id_usuario": usuario["id_usuario"],
            "id_empleado": usuario.get("id_empleado"),
            "correo": usuario["correo"],
            "nombre_completo": usuario.get("nombre_completo"),
            "rol": usuario["rol"],
        },
    }

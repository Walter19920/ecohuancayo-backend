"""Reglas de negocio de autenticación."""

from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.security import (
    INACTIVE_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    INVALID_TOKEN_MESSAGE,
    create_access_token,
    hash_password,
    verify_password,
)
from ..repositories import auth_repo, usuario_repo


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


def cambiar_mi_password(
    conn: Connection[Any],
    correo: str,
    password_actual: str,
    nueva_password: str,
) -> None:
    """Cambia la contraseña del usuario en sesión validando la actual."""
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

    if not verify_password(password_actual, usuario["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )

    usuario_repo.cambiar_password_usuario(
        conn,
        usuario["id_usuario"],
        hash_password(nueva_password),
    )

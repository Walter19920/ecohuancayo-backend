"""Endpoints de autenticación."""

from typing import Any

from fastapi import APIRouter, Depends
from psycopg import Connection

from ..core.database import get_db
from ..core.security import get_current_user
from ..schemas.auth_schema import (
    CambiarMiPasswordIn,
    LoginRequest,
    SolicitarContrasenaIn,
    TokenResponse,
    UsuarioSesion,
)
from ..schemas.usuario_schema import MensajeResponse
from ..services import auth_service, usuario_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    conn: Connection[Any] = Depends(get_db),
) -> dict[str, Any]:
    return auth_service.login(conn, payload.correo, payload.password)


@router.post("/solicitar-contrasena", response_model=MensajeResponse)
def solicitar_contrasena(
    payload: SolicitarContrasenaIn,
    conn: Connection[Any] = Depends(get_db),
) -> MensajeResponse:
    usuario_service.solicitar_cambio_contrasena(conn, payload.correo)
    return MensajeResponse(mensaje=usuario_service.MENSAJE_SOLICITUD_CONTRASENA)


@router.patch("/cambiar-password", response_model=MensajeResponse)
def cambiar_password(
    payload: CambiarMiPasswordIn,
    conn: Connection[Any] = Depends(get_db),
    usuario: dict[str, Any] = Depends(get_current_user),
) -> MensajeResponse:
    auth_service.cambiar_mi_password(
        conn,
        usuario["correo"],
        payload.password_actual,
        payload.nueva_password,
    )
    return MensajeResponse(mensaje="Contraseña actualizada correctamente")


@router.get("/me", response_model=UsuarioSesion)
def me(usuario: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return usuario

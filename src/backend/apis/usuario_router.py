"""Endpoints administrativos de usuarios."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from ..core.database import get_db
from ..core.security import require_admin
from ..schemas.paginacion_schema import RespuestaPaginada
from ..schemas.usuario_schema import (
    EstadoUsuarioUpdate,
    MensajeResponse,
    PasswordUsuarioUpdate,
    UsuarioCreate,
    UsuarioOut,
)
from ..services import usuario_service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=RespuestaPaginada[UsuarioOut])
def listar(
    pagina: int = Query(default=1, ge=1),
    tamanio_pagina: int = Query(default=5, ge=1, le=100),
    busqueda: str = Query(default=""),
    conn: Connection[Any] = Depends(get_db),
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return usuario_service.listar_paginado(
        conn, busqueda.strip(), pagina, tamanio_pagina
    )


@router.post("", response_model=MensajeResponse)
def registrar(
    payload: UsuarioCreate,
    conn: Connection[Any] = Depends(get_db),
    _admin: dict[str, Any] = Depends(require_admin),
) -> MensajeResponse:
    usuario_service.registrar(conn, payload)
    return MensajeResponse(mensaje="Usuario registrado correctamente")


@router.patch("/{id_usuario}/estado", response_model=MensajeResponse)
def cambiar_estado(
    id_usuario: int,
    payload: EstadoUsuarioUpdate,
    conn: Connection[Any] = Depends(get_db),
    _admin: dict[str, Any] = Depends(require_admin),
) -> MensajeResponse:
    usuario_service.cambiar_estado(conn, id_usuario, payload.estado)
    return MensajeResponse(mensaje="Estado del usuario actualizado correctamente")


@router.patch("/{id_usuario}/password", response_model=MensajeResponse)
def cambiar_password(
    id_usuario: int,
    payload: PasswordUsuarioUpdate,
    conn: Connection[Any] = Depends(get_db),
    _admin: dict[str, Any] = Depends(require_admin),
) -> MensajeResponse:
    usuario_service.cambiar_password(conn, id_usuario, payload.nueva_password)
    return MensajeResponse(mensaje="Contraseña actualizada correctamente")

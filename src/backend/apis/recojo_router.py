"""Endpoints de recojos."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection

from ..core.database import get_db
from ..core.security import get_current_user
from ..schemas.paginacion_schema import RespuestaPaginada
from ..schemas.recojo_schema import (
    EstadoRecojoUpdate,
    MisRecojoOut,
    RecojoCreate,
    RecojoOut,
)
from ..schemas.usuario_schema import MensajeResponse
from ..services import recojo_service

router = APIRouter(prefix="/recojos", tags=["Recojos"])

ROLES_ACTUALIZACION_ESTADO = {"ADMIN", "SUPERVISOR", "OPERADOR"}
MENSAJE_SIN_PERMISO = "No tienes permisos para actualizar el estado del recojo"
MENSAJE_EMPLEADO_REQUERIDO = "El usuario no tiene un empleado asociado"
MENSAJE_RECOJO_AJENO = "El recojo no está asignado a tu persona"


@router.get("/mis-recojos", response_model=RespuestaPaginada[MisRecojoOut])
def listar_mis_recojos(
    pagina: int = Query(default=1, ge=1),
    tamanio_pagina: int = Query(default=5, ge=1, le=100),
    id_estado: int | None = Query(default=None),
    conn: Connection = Depends(get_db),
    usuario: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Lista los recojos asignados al empleado vinculado al token JWT."""
    id_empleado = usuario.get("id_empleado")
    if id_empleado is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MENSAJE_EMPLEADO_REQUERIDO,
        )
    return recojo_service.listar_mis_recojos_paginado(
        conn, int(id_empleado), id_estado, pagina, tamanio_pagina
    )


@router.get("", response_model=RespuestaPaginada[RecojoOut])
def listar(
    pagina: int = Query(default=1, ge=1),
    tamanio_pagina: int = Query(default=5, ge=1, le=100),
    id_estado: int | None = Query(default=None),
    busqueda: str = Query(default=""),
    conn: Connection = Depends(get_db),
) -> dict[str, Any]:
    return recojo_service.listar_paginado(
        conn, id_estado, busqueda.strip(), pagina, tamanio_pagina
    )


@router.post("", response_model=MensajeResponse)
def registrar(
    payload: RecojoCreate,
    conn: Connection = Depends(get_db),
) -> MensajeResponse:
    recojo_service.registrar(conn, payload)
    return MensajeResponse(mensaje="Recojo registrado correctamente")


@router.patch("/{id_recojo}/estado", response_model=MensajeResponse)
def actualizar_estado(
    id_recojo: int,
    payload: EstadoRecojoUpdate,
    conn: Connection = Depends(get_db),
    usuario: dict[str, Any] = Depends(get_current_user),
) -> MensajeResponse:
    """Actualiza el estado; el OPERADOR solo actúa sobre sus propios recojos."""
    rol = str(usuario.get("rol", "")).strip().upper()
    if rol not in ROLES_ACTUALIZACION_ESTADO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MENSAJE_SIN_PERMISO,
        )

    if rol == "OPERADOR":
        id_empleado = usuario.get("id_empleado")
        if id_empleado is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=MENSAJE_EMPLEADO_REQUERIDO,
            )
        if not recojo_service.verificar_recojo_asignado(
            conn, int(id_empleado), id_recojo
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=MENSAJE_RECOJO_AJENO,
            )

    recojo_service.actualizar_estado(conn, id_recojo, payload.id_estado_recojo)
    return MensajeResponse(mensaje="Estado del recojo actualizado correctamente")

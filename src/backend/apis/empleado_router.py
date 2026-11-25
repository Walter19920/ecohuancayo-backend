"""Endpoints de empleados."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from ..core.database import get_db
from ..core.security import require_admin, require_gestion
from ..schemas.empleado_schema import (
    CargoAsignacion,
    EmpleadoCreate,
    EmpleadoOut,
    HistorialCargoOut,
    HistorialRecojoEmpleadoOut,
)
from ..schemas.paginacion_schema import RespuestaPaginada
from ..schemas.usuario_schema import MensajeResponse
from ..services import empleado_service

router = APIRouter(prefix="/empleados", tags=["Empleados"])


@router.get("", response_model=RespuestaPaginada[EmpleadoOut])
def listar(
    pagina: int = Query(default=1, ge=1),
    tamanio_pagina: int = Query(default=5, ge=1, le=100),
    busqueda: str = Query(default=""),
    conn: Connection[Any] = Depends(get_db),
) -> dict[str, Any]:
    return empleado_service.listar_paginado(
        conn, busqueda.strip(), pagina, tamanio_pagina
    )


@router.post("", response_model=MensajeResponse)
def registrar(
    payload: EmpleadoCreate,
    conn: Connection[Any] = Depends(get_db),
    _usuario: dict[str, Any] = Depends(require_gestion),
) -> MensajeResponse:
    empleado_service.registrar(conn, payload)
    return MensajeResponse(mensaje="Empleado registrado correctamente")


@router.post("/{id_empleado}/cargo", response_model=MensajeResponse)
def asignar_cargo(
    id_empleado: int,
    payload: CargoAsignacion,
    conn: Connection[Any] = Depends(get_db),
    _admin: dict[str, Any] = Depends(require_admin),
) -> MensajeResponse:
    empleado_service.asignar_cargo(conn, id_empleado, payload.id_cargo)
    return MensajeResponse(mensaje="Cargo asignado correctamente")


@router.get("/{id_empleado}/historial", response_model=list[HistorialCargoOut])
def historial(
    id_empleado: int,
    conn: Connection[Any] = Depends(get_db),
) -> list[dict[str, Any]]:
    return empleado_service.historial_cargos(conn, id_empleado)


@router.get(
    "/{id_empleado}/recojos",
    response_model=list[HistorialRecojoEmpleadoOut],
)
def historial_recojos(
    id_empleado: int,
    conn: Connection[Any] = Depends(get_db),
) -> list[dict[str, Any]]:
    return empleado_service.historial_recojos(conn, id_empleado)

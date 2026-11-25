"""Endpoints de flota."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from ..core.database import get_db
from ..core.security import require_gestion
from ..schemas.flota_schema import (
    EstadoVehiculoUpdate,
    VehiculoCreate,
    VehiculoOut,
)
from ..schemas.paginacion_schema import RespuestaPaginada
from ..schemas.usuario_schema import MensajeResponse
from ..services import flota_service

router = APIRouter(prefix="/flota", tags=["Flota"])


@router.get("", response_model=RespuestaPaginada[VehiculoOut])
def listar(
    pagina: int = Query(default=1, ge=1),
    tamanio_pagina: int = Query(default=5, ge=1, le=100),
    busqueda: str = Query(default=""),
    conn: Connection[Any] = Depends(get_db),
) -> dict[str, Any]:
    return flota_service.listar_paginado(conn, busqueda.strip(), pagina, tamanio_pagina)


@router.post("", response_model=MensajeResponse)
def registrar(
    payload: VehiculoCreate,
    conn: Connection[Any] = Depends(get_db),
    _usuario: dict[str, Any] = Depends(require_gestion),
) -> MensajeResponse:
    flota_service.registrar(conn, payload)
    return MensajeResponse(mensaje="Vehículo registrado correctamente")


@router.patch("/{id_vehiculo}/estado", response_model=MensajeResponse)
def actualizar_estado(
    id_vehiculo: int,
    payload: EstadoVehiculoUpdate,
    conn: Connection[Any] = Depends(get_db),
    _usuario: dict[str, Any] = Depends(require_gestion),
) -> MensajeResponse:
    flota_service.actualizar_estado(conn, id_vehiculo, payload.estado)
    return MensajeResponse(mensaje="Estado del vehículo actualizado correctamente")

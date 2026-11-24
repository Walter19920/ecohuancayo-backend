"""Endpoints de clientes."""

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from ..core.database import get_db
from ..schemas.cliente_schema import ClienteCreate, ClienteOut, ClienteUpdate
from ..schemas.paginacion_schema import RespuestaPaginada
from ..schemas.usuario_schema import MensajeResponse
from ..services import cliente_service

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=RespuestaPaginada[ClienteOut])
def listar(
    pagina: int = Query(default=1, ge=1),
    tamanio_pagina: int = Query(default=5, ge=1, le=100),
    busqueda: str = Query(default=""),
    conn: Connection = Depends(get_db),
) -> dict:
    return cliente_service.listar_paginado(
        conn, busqueda.strip(), pagina, tamanio_pagina
    )


@router.post("", response_model=MensajeResponse)
def registrar(
    payload: ClienteCreate,
    conn: Connection = Depends(get_db),
) -> MensajeResponse:
    cliente_service.registrar(conn, payload)
    return MensajeResponse(mensaje="Cliente registrado correctamente")


@router.put("/{id_cliente}", response_model=MensajeResponse)
def actualizar(
    id_cliente: int,
    payload: ClienteUpdate,
    conn: Connection = Depends(get_db),
) -> MensajeResponse:
    cliente_service.actualizar(conn, id_cliente, payload)
    return MensajeResponse(mensaje="Cliente actualizado correctamente")

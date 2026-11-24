"""Reglas de negocio de flota."""

from typing import Any

from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import flota_repo
from ..schemas.flota_schema import VehiculoCreate


def listar_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = flota_repo.listar_vehiculos_paginado(conn, busqueda, pagina, tamanio_pagina)
    return construir_respuesta_paginada(filas, pagina, tamanio_pagina)


def registrar(conn: Connection[Any], data: VehiculoCreate) -> None:
    flota_repo.registrar_vehiculo(
        conn,
        data.id_tipo_vehiculo,
        data.placa,
        data.capacidad_kg,
    )

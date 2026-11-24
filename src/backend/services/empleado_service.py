"""Reglas de negocio de empleados."""

from typing import Any

from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import empleado_repo
from ..schemas.empleado_schema import EmpleadoCreate


def listar_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = empleado_repo.listar_empleados_paginado(
        conn, busqueda, pagina, tamanio_pagina
    )
    return construir_respuesta_paginada(filas, pagina, tamanio_pagina)


def registrar(conn: Connection[Any], data: EmpleadoCreate) -> None:
    empleado_repo.registrar_empleado(
        conn,
        data.nombres,
        data.apellidos,
        data.dni,
        data.telefono,
        data.id_cargo,
    )


def asignar_cargo(
    conn: Connection[Any],
    id_empleado: int,
    id_cargo: int,
) -> None:
    empleado_repo.asignar_cargo_empleado(conn, id_empleado, id_cargo)


def historial_cargos(
    conn: Connection[Any],
    id_empleado: int,
) -> list[dict[str, Any]]:
    return empleado_repo.historial_cargos_empleado(conn, id_empleado)

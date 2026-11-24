"""Acceso a datos de empleados."""

from typing import Any

from psycopg import Connection


def listar_empleados_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_listar_empleados_paginado(%s, %s, %s)",
            (busqueda, pagina, tamanio_pagina),
        )
        return cur.fetchall()


def registrar_empleado(
    conn: Connection[Any],
    nombres: str,
    apellidos: str,
    dni: str,
    telefono: str | None,
    id_cargo: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_registrar_empleado(%s, %s, %s, %s, %s)",
            (nombres, apellidos, dni, telefono, id_cargo),
        )
    conn.commit()


def asignar_cargo_empleado(
    conn: Connection[Any],
    id_empleado: int,
    id_cargo: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_asignar_cargo_empleado(%s, %s)",
            (id_empleado, id_cargo),
        )
    conn.commit()


def historial_cargos_empleado(
    conn: Connection[Any],
    id_empleado: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_historial_cargos_empleado(%s)",
            (id_empleado,),
        )
        return cur.fetchall()

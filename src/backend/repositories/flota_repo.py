"""Acceso a datos de flota."""

from typing import Any

from psycopg import Connection


def listar_vehiculos_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_listar_vehiculos_paginado(%s, %s, %s)",
            (busqueda, pagina, tamanio_pagina),
        )
        return cur.fetchall()


def registrar_vehiculo(
    conn: Connection[Any],
    id_tipo_vehiculo: int,
    placa: str,
    capacidad_kg: float,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_registrar_vehiculo(%s, %s, %s)",
            (id_tipo_vehiculo, placa, capacidad_kg),
        )
    conn.commit()

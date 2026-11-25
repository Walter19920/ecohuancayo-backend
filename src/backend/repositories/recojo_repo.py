"""Acceso a datos de recojos."""

import json
from datetime import date, time
from typing import Any

from psycopg import Connection

from ..schemas.recojo_schema import EmpleadoParaSp, ResiduoParaSp


def listar_recojos_paginado(
    conn: Connection[Any],
    id_estado: int | None,
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_listar_recojos_paginado(%s, %s, %s, %s)",
            (id_estado, busqueda, pagina, tamanio_pagina),
        )
        return cur.fetchall()


def listar_mis_recojos_paginado(
    conn: Connection[Any],
    id_empleado: int,
    id_estado: int | None,
    pagina: int,
    tamanio_pagina: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_listar_mis_recojos_paginado(%s, %s, %s, %s)",
            (id_empleado, id_estado, pagina, tamanio_pagina),
        )
        return cur.fetchall()


def registrar_recojo_completo(
    conn: Connection[Any],
    id_vehiculo: int,
    id_centro_reciclaje: int,
    id_cliente: int,
    id_estado_recojo: int,
    fecha_recojo: date,
    hora_recojo: time,
    residuos: list[ResiduoParaSp],
    empleados: list[EmpleadoParaSp],
) -> None:
    """Serializa los residuos y empleados normalizados para el SP."""
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_registrar_recojo_completo("
            "%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)",
            (
                id_vehiculo,
                id_centro_reciclaje,
                id_cliente,
                id_estado_recojo,
                fecha_recojo,
                hora_recojo,
                json.dumps([item.model_dump() for item in residuos], default=str),
                json.dumps([item.model_dump() for item in empleados], default=str),
            ),
        )
    conn.commit()


def actualizar_estado_recojo(
    conn: Connection[Any],
    id_recojo: int,
    id_estado_recojo: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_actualizar_estado_recojo(%s, %s)",
            (id_recojo, id_estado_recojo),
        )
    conn.commit()

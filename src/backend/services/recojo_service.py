"""Reglas de negocio de recojos."""

from typing import Any

from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import recojo_repo
from ..schemas.recojo_schema import RecojoCreate


def listar_paginado(
    conn: Connection[Any],
    id_estado: int | None,
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = recojo_repo.listar_recojos_paginado(
        conn, id_estado, busqueda, pagina, tamanio_pagina
    )
    return construir_respuesta_paginada(filas, pagina, tamanio_pagina)


def listar_mis_recojos_paginado(
    conn: Connection[Any],
    id_empleado: int,
    id_estado: int | None,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = recojo_repo.listar_mis_recojos_paginado(
        conn, id_empleado, id_estado, pagina, tamanio_pagina
    )
    return construir_respuesta_paginada(filas, pagina, tamanio_pagina)


def verificar_recojo_asignado(
    conn: Connection[Any],
    id_empleado: int,
    id_recojo: int,
) -> bool:
    """Indica si el recojo figura entre los asignados al empleado."""
    pagina = 1
    tamanio_pagina = 100

    while True:
        respuesta = listar_mis_recojos_paginado(
            conn, id_empleado, None, pagina, tamanio_pagina
        )
        if any(
            int(item.get("id_recojo") or 0) == id_recojo for item in respuesta["items"]
        ):
            return True
        if pagina >= respuesta["total_paginas"]:
            return False
        pagina += 1


def registrar(conn: Connection[Any], data: RecojoCreate) -> None:
    recojo_repo.registrar_recojo_completo(
        conn,
        data.id_vehiculo,
        data.id_centro_reciclaje,
        data.id_cliente,
        data.id_estado_recojo,
        data.fecha_recojo,
        data.hora_recojo,
        [residuo.model_dump() for residuo in data.residuos],
        [empleado.model_dump() for empleado in data.empleados],
    )


def actualizar_estado(
    conn: Connection[Any],
    id_recojo: int,
    id_estado_recojo: int,
) -> None:
    recojo_repo.actualizar_estado_recojo(conn, id_recojo, id_estado_recojo)

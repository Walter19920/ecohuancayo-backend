"""Reglas de negocio de recojos."""

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import empleado_repo, recojo_repo
from ..schemas.recojo_schema import EmpleadoAsignado, RecojoCreate

ZONA_PERU = ZoneInfo("America/Lima")
MENSAJE_FECHA_PASADA = "La fecha de recojo no puede ser anterior a la fecha actual"
MENSAJE_HORA_PASADA = (
    "La hora de recojo no puede ser anterior a la hora actual "
    "para recojos programados hoy."
)
MENSAJE_EMPLEADOS_REQUERIDOS = "Debe asignar al menos 1 empleado al recojo."
MENSAJE_EMPLEADOS_MAXIMOS = "Máximo 2 empleados por recojo."
CARGOS_OPERATIVOS = {"Conductor de Unidad Pesada", "Operario de Recolección"}
MENSAJE_EMPLEADO_NO_OPERATIVO = (
    "No se puede asignar un empleado inactivo o no operativo al recojo."
)


def _ahora_en_peru() -> datetime:
    """Devuelve la hora actual en la zona horaria de Perú."""
    return datetime.now(ZONA_PERU)


def _validar_empleados_asignados(
    conn: Connection[Any],
    empleados: list[EmpleadoAsignado],
) -> None:
    """Verifica que cada operario exista, esté activo y tenga cargo operativo."""
    por_id = {
        int(fila.get("id_empleado") or 0): fila
        for fila in empleado_repo.listar_empleados(conn)
    }
    for empleado in empleados:
        fila = por_id.get(empleado.id_empleado)
        if (
            fila is None
            or fila.get("estado") is not True
            or fila.get("cargo_actual") not in CARGOS_OPERATIVOS
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_EMPLEADO_NO_OPERATIVO,
            )


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


def _validar_fecha_hora(fecha_recojo: date, hora_recojo: time, ahora: datetime) -> None:
    """Valida fecha y hora usando siempre la hora local de Perú (America/Lima).

    ``ahora`` se recibe como parámetro para que la validación no dependa de la
    hora real ni de la zona horaria del equipo donde corre la aplicación.
    """
    hoy = ahora.date()

    if fecha_recojo < hoy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_FECHA_PASADA,
        )

    if fecha_recojo == hoy:
        hora_actual = ahora.time().replace(second=0, microsecond=0, tzinfo=None)
        if hora_recojo.replace(tzinfo=None) < hora_actual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_HORA_PASADA,
            )


def registrar(conn: Connection[Any], data: RecojoCreate) -> None:
    """Valida fecha, hora y cuadrilla antes de llamar al procedimiento almacenado."""
    _validar_fecha_hora(data.fecha_recojo, data.hora_recojo, _ahora_en_peru())

    total_empleados = len(data.empleados)
    if total_empleados < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_EMPLEADOS_REQUERIDOS,
        )
    if total_empleados > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_EMPLEADOS_MAXIMOS,
        )

    _validar_empleados_asignados(conn, data.empleados)

    recojo_repo.registrar_recojo_completo(
        conn,
        data.id_vehiculo,
        data.id_centro_reciclaje,
        data.id_cliente,
        data.id_estado_recojo,
        data.fecha_recojo,
        data.hora_recojo,
        [residuo.para_sp() for residuo in data.residuos],
        [empleado.para_sp() for empleado in data.empleados],
    )


def actualizar_estado(
    conn: Connection[Any],
    id_recojo: int,
    id_estado_recojo: int,
) -> None:
    recojo_repo.actualizar_estado_recojo(conn, id_recojo, id_estado_recojo)

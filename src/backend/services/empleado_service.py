"""Reglas de negocio de empleados."""

import re
from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import empleado_repo
from ..schemas.empleado_schema import EmpleadoCreate

DNI_REGEX = re.compile(r"^\d{8}$")
MENSAJE_DNI_INVALIDO = "El DNI debe tener exactamente 8 dígitos."
MENSAJE_DNI_DUPLICADO = "Ya existe un empleado registrado con ese DNI."
MENSAJE_NOMBRES_INVALIDOS = "Los nombres no pueden estar vacíos ni contener números."
MENSAJE_APELLIDOS_INVALIDOS = (
    "Los apellidos no pueden estar vacíos ni contener números."
)


def _validar_nombre(valor: str, mensaje: str) -> None:
    """Rechaza nombres o apellidos vacíos o con dígitos."""
    texto = (valor or "").strip()
    if not texto or re.search(r"\d", texto):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=mensaje,
        )


def _validar_registro(conn: Connection[Any], data: EmpleadoCreate) -> None:
    """Valida el alta con los datos de `fn_listar_empleados()` antes del `CALL`."""
    empleados = empleado_repo.listar_empleados(conn)
    dni = data.dni.strip()

    if not DNI_REGEX.fullmatch(dni):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_DNI_INVALIDO,
        )
    if any(str(fila.get("dni") or "").strip() == dni for fila in empleados):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_DNI_DUPLICADO,
        )

    _validar_nombre(data.nombres, MENSAJE_NOMBRES_INVALIDOS)
    _validar_nombre(data.apellidos, MENSAJE_APELLIDOS_INVALIDOS)


def listar_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = empleado_repo.listar_empleados(conn)
    texto = busqueda.strip().casefold()
    if texto:
        filas = [
            fila
            for fila in filas
            if texto in str(fila.get("nombres") or "").casefold()
            or texto in str(fila.get("apellidos") or "").casefold()
            or texto in str(fila.get("cargo_actual") or "").casefold()
        ]

    total = len(filas)
    inicio = (pagina - 1) * tamanio_pagina
    items = [
        {**fila, "total_registros": total}
        for fila in filas[inicio : inicio + tamanio_pagina]
    ]
    return construir_respuesta_paginada(items, pagina, tamanio_pagina)


def registrar(conn: Connection[Any], data: EmpleadoCreate) -> None:
    _validar_registro(conn, data)
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


def historial_recojos(
    conn: Connection[Any],
    id_empleado: int,
) -> list[dict[str, Any]]:
    return empleado_repo.historial_recojos_empleado(conn, id_empleado)

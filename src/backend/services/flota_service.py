"""Reglas de negocio de flota."""

from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import flota_repo
from ..schemas.flota_schema import VehiculoCreate

ESTADOS_VEHICULO = ("Disponible", "En Ruta", "Mantenimiento", "Inactivo")
CAPACIDAD_MINIMA_KG = 100
MENSAJE_CAPACIDAD_MINIMA = "La capacidad del vehículo debe ser de al menos 100 kg."
MENSAJE_ESTADO_INVALIDO = (
    "El estado del vehículo debe ser Disponible, En Ruta, Mantenimiento o Inactivo."
)


def listar_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = flota_repo.listar_vehiculos(conn)
    texto = busqueda.strip().casefold()
    if texto:
        filas = [
            fila
            for fila in filas
            if texto in str(fila.get("placa") or "").casefold()
            or texto in str(fila.get("tipo_vehiculo") or "").casefold()
        ]

    total = len(filas)
    inicio = (pagina - 1) * tamanio_pagina
    items = [
        {**fila, "total_registros": total}
        for fila in filas[inicio : inicio + tamanio_pagina]
    ]
    return construir_respuesta_paginada(items, pagina, tamanio_pagina)


def registrar(conn: Connection[Any], data: VehiculoCreate) -> None:
    if data.capacidad_kg < CAPACIDAD_MINIMA_KG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_CAPACIDAD_MINIMA,
        )

    flota_repo.registrar_vehiculo(
        conn,
        data.id_tipo_vehiculo,
        data.placa,
        data.capacidad_kg,
    )


def actualizar_estado(
    conn: Connection[Any],
    id_vehiculo: int,
    estado: str,
) -> None:
    """Valida el estado y delega el cambio al procedimiento almacenado."""
    if estado not in ESTADOS_VEHICULO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_ESTADO_INVALIDO,
        )

    flota_repo.actualizar_estado_vehiculo(conn, id_vehiculo, estado)

"""Acceso a datos de flota."""

from decimal import Decimal
from typing import Any

from psycopg import Connection


def listar_vehiculos(conn: Connection[Any]) -> list[dict[str, Any]]:
    """Obtiene todos los vehículos desde la función almacenada permitida."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_listar_vehiculos()")
        return cur.fetchall()


def registrar_vehiculo(
    conn: Connection[Any],
    id_tipo_vehiculo: int,
    placa: str,
    capacidad_kg: Decimal,
) -> None:
    """Invoca el procedimiento con los tipos exactos de su firma."""
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_registrar_vehiculo(%s::INT, %s::VARCHAR, %s::NUMERIC)",
            (id_tipo_vehiculo, placa, capacidad_kg),
        )
    conn.commit()


def actualizar_estado_vehiculo(
    conn: Connection[Any],
    id_vehiculo: int,
    estado: str,
) -> None:
    """Actualiza el estado mediante el procedimiento almacenado permitido."""
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_actualizar_estado_vehiculo(%s, %s)",
            (id_vehiculo, estado),
        )
    conn.commit()

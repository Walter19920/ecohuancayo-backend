"""Acceso a datos de empleados."""

from typing import Any

from psycopg import Connection


def listar_empleados(conn: Connection[Any]) -> list[dict[str, Any]]:
    """Obtiene todos los empleados desde la función almacenada permitida."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_listar_empleados()")
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


def historial_recojos_empleado(
    conn: Connection[Any],
    id_empleado: int,
) -> list[dict[str, Any]]:
    """Obtiene los recojos operativos de un empleado desde la función permitida."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_historial_recojos_empleado(%s)",
            (id_empleado,),
        )
        return cur.fetchall()

"""Acceso a datos del dashboard."""

from typing import Any

from psycopg import Connection


def obtener_indicadores(conn: Connection[Any]) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_obtener_indicadores_dashboard()")
        return cur.fetchone()


def kg_por_tipo_residuo(conn: Connection[Any]) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_kg_por_tipo_residuo()")
        return cur.fetchall()

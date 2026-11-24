"""Acceso a datos de catálogos."""

from typing import Any

from psycopg import Connection


def listar_catalogos(conn: Connection[Any]) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT fn_listar_catalogos() AS catalogos")
        row = cur.fetchone()
        if not row:
            return {}
        return row.get("catalogos") or {}

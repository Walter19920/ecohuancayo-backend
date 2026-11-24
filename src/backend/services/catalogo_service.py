"""Reglas de negocio de catálogos."""

from typing import Any

from psycopg import Connection

from ..repositories import catalogo_repo


def listar(conn: Connection[Any]) -> dict[str, Any]:
    return catalogo_repo.listar_catalogos(conn)

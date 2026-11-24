"""Pool de conexiones PostgreSQL y dependencia de base de datos.

El pool se crea una sola vez en el ``lifespan`` de la aplicación y se entrega
por request mediante ``get_db``. Cualquier error de PostgreSQL se traduce a un
HTTP 400 con el mensaje limpio del ``RAISE EXCEPTION``.
"""

from collections.abc import Iterator
from typing import Any

import psycopg
from fastapi import HTTPException, Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DB_ERROR_FALLBACK = "Error en base de datos"


def create_pool(database_url: str) -> ConnectionPool:
    """Crea un pool de conexiones con filas mapeadas a diccionarios."""
    return ConnectionPool(
        conninfo=database_url,
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=10,
        open=False,
    )


def clean_database_message(error: psycopg.Error) -> str:
    """Extrae el mensaje legible del ``RAISE EXCEPTION``."""
    message = error.diag.message_primary if error.diag is not None else None
    return message or DB_ERROR_FALLBACK


def get_db(request: Request) -> Iterator[psycopg.Connection[Any]]:
    """Entrega una conexión del pool y la devuelve al terminar el request."""
    pool: ConnectionPool = request.app.state.pool
    try:
        with pool.connection() as conn:
            yield conn
    except psycopg.Error as error:
        raise HTTPException(
            status_code=400,
            detail=clean_database_message(error),
        ) from error

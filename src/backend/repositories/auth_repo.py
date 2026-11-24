"""Acceso a datos de autenticación."""

from typing import Any

from psycopg import Connection


def obtener_usuario_por_correo(
    conn: Connection[Any],
    correo: str,
) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_obtener_usuario_por_correo(%s)",
            (correo,),
        )
        return cur.fetchone()

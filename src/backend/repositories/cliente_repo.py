"""Acceso a datos de clientes."""

from typing import Any

from psycopg import Connection


def listar_clientes_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_listar_clientes_paginado(%s, %s, %s)",
            (busqueda, pagina, tamanio_pagina),
        )
        return cur.fetchall()


def listar_clientes(
    conn: Connection[Any],
    busqueda: str,
) -> list[dict[str, Any]]:
    """Busca clientes mediante la función almacenada permitida."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_listar_clientes(%s)", (busqueda,))
        return cur.fetchall()


def registrar_cliente(
    conn: Connection[Any],
    razon_social: str,
    ruc: str,
    direccion: str | None,
    correo: str | None,
    telefono: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_registrar_cliente(%s, %s, %s, %s, %s)",
            (razon_social, ruc, direccion, correo, telefono),
        )
    conn.commit()


def actualizar_cliente(
    conn: Connection[Any],
    id_cliente: int,
    razon_social: str,
    direccion: str | None,
    correo: str | None,
    telefono: str | None,
    estado: bool,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_actualizar_cliente(%s, %s, %s, %s, %s, %s)",
            (id_cliente, razon_social, direccion, correo, telefono, estado),
        )
    conn.commit()

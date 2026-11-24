"""Acceso a datos de usuarios."""

from typing import Any

from psycopg import Connection


def listar_usuarios_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_listar_usuarios_paginado(%s, %s, %s)",
            (busqueda, pagina, tamanio_pagina),
        )
        return cur.fetchall()


def registrar_usuario(
    conn: Connection[Any],
    id_empleado: int,
    correo: str,
    password_hash: str,
    rol: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_registrar_usuario(%s, %s, %s, %s)",
            (id_empleado, correo, password_hash, rol),
        )
    conn.commit()


def cambiar_estado_usuario(
    conn: Connection[Any],
    id_usuario: int,
    estado: bool,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_cambiar_estado_usuario(%s, %s)",
            (id_usuario, estado),
        )
    conn.commit()


def cambiar_password_usuario(
    conn: Connection[Any],
    id_usuario: int,
    nuevo_password_hash: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_cambiar_password_usuario(%s, %s)",
            (id_usuario, nuevo_password_hash),
        )
    conn.commit()

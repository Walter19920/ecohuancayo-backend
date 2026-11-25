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


def listar_usuarios(conn: Connection[Any]) -> list[dict[str, Any]]:
    """Obtiene todos los usuarios desde la función almacenada permitida."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_listar_usuarios()")
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


def solicitar_cambio_contrasena(conn: Connection[Any], correo: str) -> None:
    """Registra la solicitud pública mediante el procedimiento permitido."""
    with conn.cursor() as cur:
        cur.execute("CALL sp_solicitar_cambio_contrasena(%s)", (correo,))
    conn.commit()


def listar_solicitudes_contrasena(conn: Connection[Any]) -> list[dict[str, Any]]:
    """Obtiene las solicitudes pendientes desde la función permitida."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM fn_listar_solicitudes_contrasena()")
        return cur.fetchall()


def atender_solicitud_contrasena(
    conn: Connection[Any],
    id_solicitud: int,
) -> None:
    """Marca una solicitud como atendida mediante el procedimiento permitido."""
    with conn.cursor() as cur:
        cur.execute("CALL sp_atender_solicitud_contrasena(%s)", (id_solicitud,))
    conn.commit()

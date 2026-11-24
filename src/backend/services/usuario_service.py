"""Reglas de negocio de usuarios."""

from typing import Any

from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..core.security import hash_password
from ..repositories import usuario_repo
from ..schemas.usuario_schema import UsuarioCreate


def listar_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = usuario_repo.listar_usuarios_paginado(
        conn, busqueda, pagina, tamanio_pagina
    )
    return construir_respuesta_paginada(filas, pagina, tamanio_pagina)


def registrar(conn: Connection[Any], data: UsuarioCreate) -> None:
    usuario_repo.registrar_usuario(
        conn,
        data.id_empleado,
        data.correo,
        hash_password(data.password),
        data.rol,
    )


def cambiar_estado(
    conn: Connection[Any],
    id_usuario: int,
    estado: bool,
) -> None:
    usuario_repo.cambiar_estado_usuario(conn, id_usuario, estado)


def cambiar_password(
    conn: Connection[Any],
    id_usuario: int,
    nueva_password: str,
) -> None:
    usuario_repo.cambiar_password_usuario(
        conn,
        id_usuario,
        hash_password(nueva_password),
    )

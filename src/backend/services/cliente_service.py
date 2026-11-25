"""Reglas de negocio de clientes."""

from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import cliente_repo, usuario_repo
from ..schemas.cliente_schema import ClienteCreate, ClienteUpdate

DOMINIO_INTERNO = "@ecohuancayo.pe"
MENSAJE_DOMINIO_RESERVADO = (
    "El correo @ecohuancayo.pe está reservado para usuarios internos."
)
MENSAJE_CLIENTE_DUPLICADO = "El correo ya pertenece a otro cliente."
MENSAJE_USUARIO_DUPLICADO = "El correo ya pertenece a un usuario del sistema."


def _validar_correo(
    conn: Connection[Any],
    correo: str | None,
    id_cliente_excluido: int | None = None,
) -> None:
    """Rechaza el dominio interno y correos ya usados por clientes o usuarios."""
    if correo is None or not str(correo).strip():
        return

    normalizado = str(correo).strip().casefold()
    if normalizado.endswith(DOMINIO_INTERNO):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_DOMINIO_RESERVADO,
        )

    for fila in cliente_repo.listar_clientes(conn, normalizado):
        correo_cliente = str(fila.get("correo") or "").strip().casefold()
        if (
            correo_cliente == normalizado
            and fila.get("id_cliente") != id_cliente_excluido
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_CLIENTE_DUPLICADO,
            )

    for fila in usuario_repo.listar_usuarios(conn):
        correo_usuario = str(fila.get("correo") or "").strip().casefold()
        if correo_usuario == normalizado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_USUARIO_DUPLICADO,
            )


def listar_paginado(
    conn: Connection[Any],
    busqueda: str,
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    filas = cliente_repo.listar_clientes_paginado(
        conn, busqueda, pagina, tamanio_pagina
    )
    return construir_respuesta_paginada(filas, pagina, tamanio_pagina)


def registrar(conn: Connection[Any], data: ClienteCreate) -> None:
    _validar_correo(conn, data.correo)
    cliente_repo.registrar_cliente(
        conn,
        data.razon_social,
        data.ruc,
        data.direccion,
        data.correo,
        data.telefono,
    )


def actualizar(
    conn: Connection[Any],
    id_cliente: int,
    data: ClienteUpdate,
) -> None:
    _validar_correo(conn, data.correo, id_cliente)
    cliente_repo.actualizar_cliente(
        conn,
        id_cliente,
        data.razon_social,
        data.direccion,
        data.correo,
        data.telefono,
        data.estado,
    )

"""Reglas de negocio de clientes."""

from typing import Any

from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..repositories import cliente_repo
from ..schemas.cliente_schema import ClienteCreate, ClienteUpdate


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
    cliente_repo.actualizar_cliente(
        conn,
        id_cliente,
        data.razon_social,
        data.direccion,
        data.correo,
        data.telefono,
        data.estado,
    )

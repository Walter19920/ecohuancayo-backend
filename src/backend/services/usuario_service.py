"""Reglas de negocio de usuarios."""

from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection

from ..core.paginacion import construir_respuesta_paginada
from ..core.security import hash_password
from ..repositories import cliente_repo, usuario_repo
from ..schemas.usuario_schema import UsuarioCreate

DOMINIO_INTERNO = "@ecohuancayo.pe"
MENSAJE_DOMINIO_INVALIDO = "El correo del usuario debe terminar en @ecohuancayo.pe."
MENSAJE_CORREO_USUARIO = "El correo ya pertenece a un usuario del sistema."
MENSAJE_CORREO_CLIENTE = "El correo ya pertenece a un cliente."
MENSAJE_SOLICITUD_CONTRASENA = (
    "Si el correo pertenece a una cuenta activa, se notificó al Administrador."
)
ROLES_SOLICITUD = {
    "ADMIN": "Administrador",
    "SUPERVISOR": "Supervisor",
    "OPERADOR": "Operador",
}


def _validar_correo_interno(conn: Connection[Any], correo: str) -> None:
    """Exige el dominio interno y descarta duplicados con `fn_` permitidas."""
    normalizado = correo.strip().casefold()
    if not normalizado.endswith(DOMINIO_INTERNO):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_DOMINIO_INVALIDO,
        )

    for fila in usuario_repo.listar_usuarios(conn):
        if str(fila.get("correo") or "").strip().casefold() == normalizado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_CORREO_USUARIO,
            )

    for fila in cliente_repo.listar_clientes(conn, normalizado):
        if str(fila.get("correo") or "").strip().casefold() == normalizado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_CORREO_CLIENTE,
            )


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
    _validar_correo_interno(conn, data.correo)
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


def solicitar_cambio_contrasena(conn: Connection[Any], correo: str) -> None:
    """Registra la solicitud sin revelar si la cuenta existe o está activa."""
    try:
        usuario_repo.solicitar_cambio_contrasena(conn, correo)
    except Exception:
        # El endpoint público siempre devuelve la misma confirmación genérica.
        return


def listar_solicitudes_contrasena(conn: Connection[Any]) -> list[dict[str, Any]]:
    filas = usuario_repo.listar_solicitudes_contrasena(conn)
    return [
        {
            **fila,
            "rol": ROLES_SOLICITUD.get(
                str(fila.get("rol") or "").strip().upper(),
                str(fila.get("rol") or "").strip() or "—",
            ),
        }
        for fila in filas
    ]


def atender_solicitud_contrasena(
    conn: Connection[Any],
    id_solicitud: int,
) -> None:
    usuario_repo.atender_solicitud_contrasena(conn, id_solicitud)

"""Endpoints de autenticación."""

from typing import Any

from fastapi import APIRouter, Depends
from psycopg import Connection

from ..core.database import get_db
from ..core.security import get_current_user
from ..schemas.auth_schema import LoginRequest, TokenResponse, UsuarioSesion
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    conn: Connection[Any] = Depends(get_db),
) -> dict[str, Any]:
    return auth_service.login(conn, payload.correo, payload.password)


@router.get("/me", response_model=UsuarioSesion)
def me(usuario: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return usuario

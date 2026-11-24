"""Schemas de autenticación."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    correo: str = Field(min_length=3)
    password: str = Field(min_length=1)


class UsuarioSesion(BaseModel):
    id_usuario: int
    id_empleado: int | None = None
    correo: str
    nombre_completo: str | None = None
    rol: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioSesion

"""Schemas de autenticación."""

import re

from pydantic import BaseModel, Field, field_validator

CORREO_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


class LoginRequest(BaseModel):
    correo: str = Field(min_length=3)
    password: str = Field(min_length=1)


class SolicitarContrasenaIn(BaseModel):
    """Correo normalizado de la solicitud pública de restablecimiento."""

    correo: str = Field(min_length=3, max_length=254)

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, valor: str) -> str:
        correo = valor.strip().casefold()
        if not CORREO_PATTERN.fullmatch(correo):
            raise ValueError("Ingresa un correo válido.")
        return correo


class CambiarMiPasswordIn(BaseModel):
    password_actual: str = Field(min_length=1)
    nueva_password: str = Field(min_length=8)


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

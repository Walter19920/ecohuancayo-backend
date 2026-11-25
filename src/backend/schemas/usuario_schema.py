"""Schemas de usuarios."""

from datetime import datetime

from pydantic import BaseModel, Field


class UsuarioOut(BaseModel):
    id_usuario: int
    id_empleado: int | None = None
    nombre_completo: str | None = None
    dni: str | None = None
    correo: str
    rol: str
    estado: bool
    fecha_creacion: datetime | None = None
    total_registros: int = 0


class UsuarioCreate(BaseModel):
    id_empleado: int
    correo: str = Field(min_length=3)
    password: str = Field(min_length=8)
    rol: str = "OPERADOR"


class EstadoUsuarioUpdate(BaseModel):
    estado: bool


class PasswordUsuarioUpdate(BaseModel):
    nueva_password: str = Field(min_length=8)


class SolicitudContrasenaOut(BaseModel):
    id_solicitud: int
    id_usuario: int
    nombre_completo: str | None = None
    correo: str
    rol: str
    fecha_solicitud: datetime | None = None


class MensajeResponse(BaseModel):
    mensaje: str

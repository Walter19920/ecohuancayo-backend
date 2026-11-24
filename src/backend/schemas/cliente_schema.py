"""Schemas de clientes."""

from pydantic import BaseModel, Field


class ClienteOut(BaseModel):
    id_cliente: int
    razon_social: str
    ruc: str | None = None
    direccion: str | None = None
    correo: str | None = None
    telefono: str | None = None
    estado: bool
    total_registros: int = 0


class ClienteCreate(BaseModel):
    razon_social: str = Field(min_length=1)
    ruc: str = Field(min_length=11, max_length=11)
    direccion: str | None = None
    correo: str | None = None
    telefono: str | None = None


class ClienteUpdate(BaseModel):
    razon_social: str = Field(min_length=1)
    direccion: str | None = None
    correo: str | None = None
    telefono: str | None = None
    estado: bool = True

"""Schemas de empleados."""

from datetime import date

from pydantic import BaseModel, Field


class EmpleadoOut(BaseModel):
    id_empleado: int
    nombres: str
    apellidos: str
    dni: str | None = None
    telefono: str | None = None
    id_cargo_actual: int | None = None
    cargo_actual: str | None = None
    estado: bool
    total_registros: int = 0


class EmpleadoCreate(BaseModel):
    nombres: str = Field(min_length=1)
    apellidos: str = Field(min_length=1)
    dni: str = Field(min_length=8, max_length=8)
    telefono: str | None = None
    id_cargo: int


class CargoAsignacion(BaseModel):
    id_cargo: int


class HistorialCargoOut(BaseModel):
    id_empleado_cargo: int
    nombre_cargo: str
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: bool

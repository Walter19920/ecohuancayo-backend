"""Schemas de flota."""

from pydantic import BaseModel, Field


class VehiculoOut(BaseModel):
    id_vehiculo: int
    id_tipo_vehiculo: int | None = None
    tipo_vehiculo: str | None = None
    placa: str
    capacidad_kg: float | None = None
    estado: str
    total_registros: int = 0


class VehiculoCreate(BaseModel):
    id_tipo_vehiculo: int
    placa: str = Field(min_length=1)
    capacidad_kg: float = Field(gt=0)


class EstadoVehiculoUpdate(BaseModel):
    estado: str = Field(min_length=1)

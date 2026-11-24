"""Schemas de catálogos."""

from pydantic import BaseModel, Field


class CatalogosOut(BaseModel):
    distritos: list[dict] = Field(default_factory=list)
    cargos: list[dict] = Field(default_factory=list)
    tipos_vehiculo: list[dict] = Field(default_factory=list)
    tipos_residuo: list[dict] = Field(default_factory=list)
    estados_recojo: list[dict] = Field(default_factory=list)
    centros_reciclaje: list[dict] = Field(default_factory=list)

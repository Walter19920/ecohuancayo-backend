"""Schemas de catálogos."""

from pydantic import BaseModel, ConfigDict, Field


class CatalogosOut(BaseModel):
    """Devuelve el JSONB completo de ``fn_listar_catalogos`` sin recortar claves."""

    model_config = ConfigDict(extra="allow")

    distritos: list[dict] = Field(default_factory=list)
    cargos: list[dict] = Field(default_factory=list)
    tipos_vehiculo: list[dict] = Field(default_factory=list)
    tipos_residuo: list[dict] = Field(default_factory=list)
    estados_recojo: list[dict] = Field(default_factory=list)
    centros_reciclaje: list[dict] = Field(default_factory=list)

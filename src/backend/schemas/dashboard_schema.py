"""Schemas del dashboard."""

from pydantic import BaseModel


class IndicadoresOut(BaseModel):
    total_recojos: int
    total_kg_reciclados: float
    clientes_activos: int
    vehiculos_disponibles: int
    recojos_completados: int
    recojos_pendientes: int


class KgPorTipoResiduoOut(BaseModel):
    tipo_residuo: str
    total_kg: float

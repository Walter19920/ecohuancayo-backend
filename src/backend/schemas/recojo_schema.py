"""Schemas de recojos."""

from datetime import date, time

from pydantic import BaseModel, Field


class RecojoOut(BaseModel):
    id_recojo: int
    cliente: str | None = None
    ruc: str | None = None
    centro_reciclaje: str | None = None
    distrito_destino: str | None = None
    vehiculo_placa: str | None = None
    id_estado_recojo: int | None = None
    estado_recojo: str | None = None
    fecha_recojo: date | None = None
    hora_recojo: time | None = None
    total_kg: float | None = None
    total_registros: int = 0


class MisRecojoOut(BaseModel):
    """Detalle de un recojo asignado al operador autenticado."""

    id_recojo: int
    cliente: str | None = None
    ruc: str | None = None
    direccion_cliente: str | None = None
    telefono_cliente: str | None = None
    centro_reciclaje: str | None = None
    distrito_destino: str | None = None
    vehiculo_placa: str | None = None
    rol_en_recojo: str | None = None
    id_estado_recojo: int | None = None
    estado_recojo: str | None = None
    fecha_recojo: date | None = None
    hora_recojo: time | None = None
    total_kg: float | None = None
    total_registros: int = 0


class ResiduoDetalle(BaseModel):
    id_tipo_residuo: int
    peso_kg: float = Field(gt=0)


class EmpleadoAsignado(BaseModel):
    id_empleado: int


class RecojoCreate(BaseModel):
    id_vehiculo: int
    id_centro_reciclaje: int
    id_cliente: int
    id_estado_recojo: int
    fecha_recojo: date
    hora_recojo: time
    residuos: list[ResiduoDetalle] = Field(min_length=1)
    empleados: list[EmpleadoAsignado] = Field(default_factory=list)


class EstadoRecojoUpdate(BaseModel):
    id_estado_recojo: int

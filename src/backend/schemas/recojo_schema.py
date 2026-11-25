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


class ResiduoParaSp(BaseModel):
    """Fila normalizada del JSON de residuos que consume el procedimiento."""

    id_tipo_residuo: int
    cantidad_kg: float = Field(gt=0)


class ResiduoDetalle(BaseModel):
    """Residuo tal como lo envía el frontend (clave pública ``peso_kg``)."""

    id_tipo_residuo: int
    peso_kg: float = Field(gt=0)

    def para_sp(self) -> ResiduoParaSp:
        """Traduce ``peso_kg`` a la clave ``cantidad_kg`` que lee el procedimiento."""
        return ResiduoParaSp(
            id_tipo_residuo=self.id_tipo_residuo,
            cantidad_kg=self.peso_kg,
        )


DESCRIPCION_EMPLEADO_POR_DEFECTO = "Operario asignado"


class EmpleadoParaSp(BaseModel):
    """Fila normalizada del JSON de empleados que consume el procedimiento."""

    id_empleado: int
    descripcion: str = Field(min_length=1)


class EmpleadoAsignado(BaseModel):
    """Empleado tal como lo envía el frontend (``descripcion`` es opcional)."""

    id_empleado: int
    descripcion: str | None = None

    def para_sp(self) -> EmpleadoParaSp:
        """Garantiza una descripción no vacía en el JSON del procedimiento."""
        descripcion = (self.descripcion or "").strip()
        return EmpleadoParaSp(
            id_empleado=self.id_empleado,
            descripcion=descripcion or DESCRIPCION_EMPLEADO_POR_DEFECTO,
        )


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

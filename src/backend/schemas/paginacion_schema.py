"""Schema genérico de respuesta paginada para los listados de la API."""

from pydantic import BaseModel


class RespuestaPaginada[T](BaseModel):
    """Envelope estándar de los endpoints GET paginados."""

    items: list[T]
    total: int
    pagina: int
    tamanio_pagina: int
    total_paginas: int

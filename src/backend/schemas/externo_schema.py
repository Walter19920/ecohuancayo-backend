"""Schemas de servicios externos.

La respuesta exitosa conserva el payload del proveedor y agrega ``manual=False``.
Si el proveedor falla, se devuelve ``manual=True`` con un mensaje para que el
usuario complete los datos manualmente.
"""

from pydantic import BaseModel, ConfigDict


class RespuestaExterna(BaseModel):
    model_config = ConfigDict(extra="allow")

    manual: bool
    mensaje: str | None = None

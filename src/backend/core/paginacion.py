"""Construcción de la respuesta paginada estándar a partir de filas de ``fn_...``.

Las funciones almacenadas devuelven ``total_registros`` en cada fila; cuando no
hay filas el total es cero.
"""

import math
from typing import Any


def construir_respuesta_paginada(
    filas: list[dict[str, Any]],
    pagina: int,
    tamanio_pagina: int,
) -> dict[str, Any]:
    """Empaqueta las filas en el contrato ``{items, total, pagina, ...}``."""
    total = int(filas[0].get("total_registros") or 0) if filas else 0
    total_paginas = (
        math.ceil(total / tamanio_pagina) if total and tamanio_pagina > 0 else 0
    )
    return {
        "items": filas,
        "total": total,
        "pagina": pagina,
        "tamanio_pagina": tamanio_pagina,
        "total_paginas": total_paginas,
    }

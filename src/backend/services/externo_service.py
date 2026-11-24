"""Integración con servicios externos y fallback manual.

Todas las llamadas usan ``httpx.AsyncClient`` con timeout de 5 segundos y
configuración desde variables de entorno. Si el proveedor falla, se devuelve
``{"manual": true, ...}`` para que el dato se complete a mano.
"""

from typing import Any

import httpx

from ..core.config import get_settings

FALLBACK_MESSAGE = (
    "El servicio externo no está disponible. Puede completar los datos manualmente."
)


def _fallback() -> dict[str, Any]:
    return {"manual": True, "mensaje": FALLBACK_MESSAGE}


def _success(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return {**data, "manual": False}
    return {"datos": data, "manual": False}


async def clima_huancayo() -> dict[str, Any]:
    """Consulta el clima actual de Huancayo en Open-Meteo."""
    settings = get_settings()
    params = {
        "latitude": settings.huancayo_lat,
        "longitude": settings.huancayo_lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        # Huancayo usa UTC-5 todo el año; Open-Meteo debe devolver la hora local.
        "timezone": "America/Lima",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.open_meteo_url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return _fallback()
    return _success(data)


async def consultar_ruc(ruc: str) -> dict[str, Any]:
    """Consulta los datos de un RUC en el proveedor externo."""
    settings = get_settings()
    url = f"{settings.apis_peru_base_url.rstrip('/')}/ruc/{ruc}"
    params = {"token": settings.apis_peru_token}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return _fallback()
    return _success(data)


async def consultar_dni(dni: str) -> dict[str, Any]:
    """Consulta los datos de un DNI en el proveedor externo."""
    settings = get_settings()
    url = f"{settings.apis_peru_base_url.rstrip('/')}/dni/{dni}"
    params = {"token": settings.apis_peru_token}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return _fallback()
    return _success(data)

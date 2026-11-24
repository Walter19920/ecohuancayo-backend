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
    """Consulta el clima actual de Huancayo en WeatherAPI.

    La respuesta se adapta al contrato que ya consume el frontend: ``current`` con
    ``temperature_2m``, ``relative_humidity_2m`` y ``wind_speed_10m``, sus unidades
    y la zona horaria de Lima.
    """
    settings = get_settings()
    if not (settings.weather_api_key or "").strip():
        return _fallback()

    url = f"{settings.weather_api_base_url.rstrip('/')}/current.json"
    params = {
        "key": settings.weather_api_key,
        "q": f"{settings.huancayo_lat},{settings.huancayo_lon}",
        "lang": "es",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        actual = data["current"]
        ultima_actualizacion = str(actual.get("last_updated", "")).replace(" ", "T")
        clima = {
            "current": {
                "temperature_2m": actual["temp_c"],
                "relative_humidity_2m": actual["humidity"],
                "wind_speed_10m": actual["wind_kph"],
                "time": ultima_actualizacion,
            },
            "current_units": {
                "temperature_2m": "°C",
                "relative_humidity_2m": "%",
                "wind_speed_10m": "km/h",
            },
            # Huancayo usa UTC-5 todo el año, igual que el contrato anterior.
            "timezone": "America/Lima",
            "utc_offset_seconds": -18000,
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return _fallback()
    return _success(clima)


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

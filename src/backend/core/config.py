"""Configuración central de la aplicación.

Todas las credenciales y parámetros de despliegue se leen desde variables de
entorno (o desde un archivo ``.env`` local). Nunca se hardcodean valores.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno requeridas por EcoHuancayo S.A.C. Backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    apis_peru_token: str
    apis_peru_base_url: str
    weather_api_base_url: str = "https://api.weatherapi.com/v1"
    weather_api_key: str = ""
    huancayo_lat: float = -12.0651
    huancayo_lon: float = -75.2049

    @property
    def cors_origin_list(self) -> list[str]:
        """Convierte ``CORS_ORIGINS`` (separado por comas) en una lista limpia."""
        return [
            origen.strip() for origen in self.cors_origins.split(",") if origen.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada para toda la vida del proceso."""
    return Settings()

"""Aplicación FastAPI de EcoHuancayo S.A.C. Backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import ConnectionPool

from .apis import (
    auth_router,
    catalogo_router,
    cliente_router,
    dashboard_router,
    empleado_router,
    externo_router,
    flota_router,
    recojo_router,
    usuario_router,
)
from .core.config import get_settings
from .core.database import create_pool

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Abre el pool de conexiones al iniciar y lo cierra al detener la app."""
    settings = get_settings()
    pool: ConnectionPool = create_pool(settings.database_url)
    pool.open()
    app.state.pool = pool
    try:
        yield
    finally:
        pool.close()


settings = get_settings()

app = FastAPI(
    title="EcoHuancayo S.A.C. Backend",
    description="API de gestión de recojo de residuos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix=API_PREFIX)
app.include_router(usuario_router.router, prefix=API_PREFIX)
app.include_router(cliente_router.router, prefix=API_PREFIX)
app.include_router(empleado_router.router, prefix=API_PREFIX)
app.include_router(flota_router.router, prefix=API_PREFIX)
app.include_router(catalogo_router.router, prefix=API_PREFIX)
app.include_router(recojo_router.router, prefix=API_PREFIX)
app.include_router(dashboard_router.router, prefix=API_PREFIX)
app.include_router(externo_router.router, prefix=API_PREFIX)


@app.get("/health", tags=["Salud"])
def health() -> dict[str, str]:
    return {"status": "ok"}

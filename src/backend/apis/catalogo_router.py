"""Endpoints de catálogos."""

from typing import Any

from fastapi import APIRouter, Depends
from psycopg import Connection

from ..core.database import get_db
from ..schemas.catalogo_schema import CatalogosOut
from ..services import catalogo_service

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


@router.get("", response_model=CatalogosOut)
def listar(conn: Connection[Any] = Depends(get_db)) -> dict[str, Any]:
    return catalogo_service.listar(conn)

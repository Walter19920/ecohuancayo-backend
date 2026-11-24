"""Endpoints del dashboard."""

from typing import Any

from fastapi import APIRouter, Depends
from psycopg import Connection

from ..core.database import get_db
from ..schemas.dashboard_schema import IndicadoresOut, KgPorTipoResiduoOut
from ..services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/indicadores", response_model=IndicadoresOut)
def indicadores(conn: Connection[Any] = Depends(get_db)) -> dict[str, Any]:
    return dashboard_service.indicadores(conn)


@router.get("/kg-por-tipo-residuo", response_model=list[KgPorTipoResiduoOut])
def kg_por_tipo_residuo(
    conn: Connection[Any] = Depends(get_db),
) -> list[dict[str, Any]]:
    return dashboard_service.kg_por_tipo_residuo(conn)

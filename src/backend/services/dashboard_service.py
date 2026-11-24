"""Reglas de negocio del dashboard."""

from typing import Any

from psycopg import Connection

from ..repositories import dashboard_repo


def indicadores(conn: Connection[Any]) -> dict[str, Any]:
    return dashboard_repo.obtener_indicadores(conn) or {
        "total_recojos": 0,
        "total_kg_reciclados": 0.0,
        "clientes_activos": 0,
        "vehiculos_disponibles": 0,
        "recojos_completados": 0,
        "recojos_pendientes": 0,
    }


def kg_por_tipo_residuo(conn: Connection[Any]) -> list[dict[str, Any]]:
    return dashboard_repo.kg_por_tipo_residuo(conn)

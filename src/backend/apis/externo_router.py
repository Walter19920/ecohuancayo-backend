"""Endpoints de servicios externos."""

from typing import Any

from fastapi import APIRouter

from ..schemas.externo_schema import RespuestaExterna
from ..services import externo_service

router = APIRouter(prefix="/externo", tags=["Servicios externos"])


@router.get("/clima-huancayo", response_model=RespuestaExterna)
async def clima_huancayo() -> dict[str, Any]:
    return await externo_service.clima_huancayo()


@router.get("/ruc/{ruc}", response_model=RespuestaExterna)
async def consultar_ruc(ruc: str) -> dict[str, Any]:
    return await externo_service.consultar_ruc(ruc)


@router.get("/dni/{dni}", response_model=RespuestaExterna)
async def consultar_dni(dni: str) -> dict[str, Any]:
    return await externo_service.consultar_dni(dni)

"""Pruebas básicas de la API con conexión de base de datos simulada.

Las variables de entorno se definen antes de importar la aplicación para que
``Settings`` no dependa de un ``.env`` real. ``get_db`` se reemplaza con una
conexión falsa mediante ``dependency_overrides``; así las pruebas no necesitan
PostgreSQL ni red.
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "postgresql://usuario:clave@localhost:5432/pruebas"
os.environ["JWT_SECRET"] = "clave-de-prueba"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_MINUTES"] = "60"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"
os.environ["APIS_PERU_TOKEN"] = "token-de-prueba"
os.environ["APIS_PERU_BASE_URL"] = "https://api.example.test"
os.environ["OPEN_METEO_URL"] = "https://api.open-meteo.test/v1/forecast"
os.environ["HUANCAYO_LAT"] = "-12.0651"
os.environ["HUANCAYO_LON"] = "-75.2049"

from backend.core.database import get_db  # noqa: E402
from backend.core.security import (  # noqa: E402
    create_access_token,
    hash_password,
)
from backend.main import app  # noqa: E402
from backend.services.externo_service import clima_huancayo  # noqa: E402

PASSWORD = "Secreta123"
PASSWORD_HASH = hash_password(PASSWORD)


class FakeCursor:
    """Cursor mínimo que registra la consulta y devuelve filas preparadas."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.query: str | None = None
        self.params: Any = None

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, query: str, params: Any = None) -> None:
        self.query = query
        self.params = params

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._rows)


class FakeConnection:
    """Conexión falsa que entrega un cursor por cada operación esperada."""

    def __init__(self, *results: list[dict[str, Any]]) -> None:
        self._results = list(results)
        self.cursors: list[FakeCursor] = []
        self.commits = 0

    def cursor(self, *args: Any, **kwargs: Any) -> FakeCursor:
        rows = self._results.pop(0) if self._results else []
        cursor = FakeCursor(rows)
        self.cursors.append(cursor)
        return cursor

    def commit(self) -> None:
        self.commits += 1


def use_connection(*results: list[dict[str, Any]]) -> FakeConnection:
    conn = FakeConnection(*results)
    app.dependency_overrides[get_db] = lambda: conn
    return conn


@pytest.fixture(autouse=True)
def clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    # Sin ``with`` para no ejecutar el lifespan (no se abre el pool real).
    return TestClient(app)


def usuario(
    *,
    correo: str = "admin@ecohuancayo.pe",
    rol: str = "ADMIN",
    estado: bool = True,
    password_hash: str = PASSWORD_HASH,
) -> dict[str, Any]:
    return {
        "id_usuario": 1,
        "id_empleado": 10,
        "correo": correo,
        "password_hash": password_hash,
        "nombre_completo": "Administrador",
        "rol": rol,
        "estado": estado,
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rutas_registradas(client: TestClient) -> None:
    rutas = set(app.openapi()["paths"])
    esperadas = {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/usuarios",
        "/api/v1/clientes",
        "/api/v1/empleados",
        "/api/v1/flota",
        "/api/v1/catalogos",
        "/api/v1/recojos",
        "/api/v1/recojos/mis-recojos",
        "/api/v1/dashboard/indicadores",
        "/api/v1/dashboard/kg-por-tipo-residuo",
        "/api/v1/externo/clima-huancayo",
        "/api/v1/externo/ruc/{ruc}",
        "/api/v1/externo/dni/{dni}",
    }
    assert esperadas <= rutas


def test_login_correcto(client: TestClient) -> None:
    use_connection([usuario()])

    response = client.post(
        "/api/v1/auth/login",
        json={"correo": "admin@ecohuancayo.pe", "password": PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["usuario"]["rol"] == "ADMIN"


def test_login_usuario_inactivo(client: TestClient) -> None:
    use_connection([usuario(estado=False)])

    response = client.post(
        "/api/v1/auth/login",
        json={"correo": "admin@ecohuancayo.pe", "password": PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Usuario inactivo. Contacte al administrador"


def test_login_password_incorrecta(client: TestClient) -> None:
    use_connection([usuario()])

    response = client.post(
        "/api/v1/auth/login",
        json={"correo": "admin@ecohuancayo.pe", "password": "incorrecta"},
    )

    assert response.status_code == 401


def test_usuarios_requiere_autenticacion(client: TestClient) -> None:
    use_connection()

    response = client.get("/api/v1/usuarios")

    assert response.status_code == 401


def test_listar_usuarios_como_admin(client: TestClient) -> None:
    fila = {
        "id_usuario": 1,
        "id_empleado": 10,
        "nombre_completo": "Administrador",
        "dni": "12345678",
        "correo": "admin@ecohuancayo.pe",
        "rol": "ADMIN",
        "estado": True,
        "fecha_creacion": datetime.now(UTC),
        "total_registros": 1,
    }
    use_connection([usuario()], [fila])

    token = create_access_token("admin@ecohuancayo.pe")
    response = client.get(
        "/api/v1/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["correo"] == "admin@ecohuancayo.pe"
    assert body["total"] == 1
    assert body["total_paginas"] == 1


def test_listar_catalogos(client: TestClient) -> None:
    catalogos = {
        "distritos": [{"id": 1, "nombre": "Huancayo"}],
        "cargos": [],
        "tipos_vehiculo": [],
        "tipos_residuo": [],
        "estados_recojo": [],
        "centros_reciclaje": [],
    }
    use_connection([{"catalogos": catalogos}])

    response = client.get("/api/v1/catalogos")

    assert response.status_code == 200
    assert response.json()["distritos"][0]["nombre"] == "Huancayo"


def test_listar_recojos_con_filtro(client: TestClient) -> None:
    fila = {
        "id_recojo": 5,
        "cliente": "Cliente Demo",
        "ruc": "20123456789",
        "centro_reciclaje": "Centro Huancayo",
        "distrito_destino": "El Tambo",
        "vehiculo_placa": "ABC-123",
        "id_estado_recojo": 2,
        "estado_recojo": "PENDIENTE",
        "fecha_recojo": "2026-11-22",
        "hora_recojo": "08:30:00",
        "total_kg": 12.5,
        "total_registros": 1,
    }
    conn = use_connection([fila])

    response = client.get("/api/v1/recojos", params={"id_estado": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id_recojo"] == 5
    assert body["total"] == 1
    assert body["pagina"] == 1
    assert body["tamanio_pagina"] == 5
    assert conn.cursors[0].params == (2, "", 1, 5)


def test_listar_mis_recojos_usa_id_empleado_del_token(client: TestClient) -> None:
    fila = {
        "id_recojo": 9,
        "cliente": "Cliente Operador",
        "ruc": "20123456789",
        "direccion_cliente": "Av. Real 123",
        "telefono_cliente": "998877665",
        "centro_reciclaje": "Centro Huancayo",
        "distrito_destino": "El Tambo",
        "vehiculo_placa": "ABC-123",
        "rol_en_recojo": "OPERADOR",
        "id_estado_recojo": 2,
        "estado_recojo": "EN RUTA",
        "fecha_recojo": "2026-11-23",
        "hora_recojo": "09:00:00",
        "total_kg": 8.25,
        "total_registros": 1,
    }
    conn = use_connection(
        [usuario(correo="operador@ecohuancayo.pe", rol="OPERADOR")],
        [fila],
    )

    token = create_access_token(
        "operador@ecohuancayo.pe", {"id_empleado": 10, "rol": "OPERADOR"}
    )
    response = client.get(
        "/api/v1/recojos/mis-recojos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id_recojo"] == 9
    assert conn.cursors[1].params == (10, None, 1, 5)


def test_actualizar_estado_recojo_operador_propio(client: TestClient) -> None:
    fila = {
        "id_recojo": 9,
        "cliente": "Cliente Operador",
        "id_estado_recojo": 1,
        "estado_recojo": "PROGRAMADO",
        "total_registros": 1,
    }
    conn = use_connection(
        [usuario(correo="operador@ecohuancayo.pe", rol="OPERADOR")],
        [fila],
        [],
    )
    token = create_access_token(
        "operador@ecohuancayo.pe", {"id_empleado": 10, "rol": "OPERADOR"}
    )
    response = client.patch(
        "/api/v1/recojos/9/estado",
        json={"id_estado_recojo": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"mensaje": "Estado del recojo actualizado correctamente"}
    assert "fn_listar_mis_recojos_paginado" in (conn.cursors[1].query or "")
    assert conn.cursors[1].params == (10, None, 1, 100)
    assert conn.cursors[2].params == (9, 2)
    assert "sp_actualizar_estado_recojo" in (conn.cursors[2].query or "")
    assert conn.commits == 1


def test_actualizar_estado_recojo_operador_ajeno_devuelve_403(
    client: TestClient,
) -> None:
    conn = use_connection(
        [usuario(correo="operador@ecohuancayo.pe", rol="OPERADOR")],
        [],
    )
    token = create_access_token(
        "operador@ecohuancayo.pe", {"id_empleado": 10, "rol": "OPERADOR"}
    )
    response = client.patch(
        "/api/v1/recojos/9/estado",
        json={"id_estado_recojo": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "El recojo no está asignado a tu persona"
    assert len(conn.cursors) == 2
    assert conn.commits == 0


def test_actualizar_estado_recojo_sin_token_devuelve_401(
    client: TestClient,
) -> None:
    use_connection()

    response = client.patch(
        "/api/v1/recojos/9/estado",
        json={"id_estado_recojo": 2},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("rol", ["ADMIN", "SUPERVISOR"])
def test_actualizar_estado_recojo_roles_generales(
    client: TestClient,
    rol: str,
) -> None:
    correo = f"{rol.lower()}@ecohuancayo.pe"
    conn = use_connection([usuario(correo=correo, rol=rol)], [])
    token = create_access_token(correo, {"rol": rol})

    response = client.patch(
        "/api/v1/recojos/9/estado",
        json={"id_estado_recojo": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(conn.cursors) == 2
    assert conn.cursors[1].query == "CALL sp_actualizar_estado_recojo(%s, %s)"
    assert conn.cursors[1].params == (9, 3)
    assert conn.commits == 1


def test_registrar_recojo_envia_jsonb(client: TestClient) -> None:
    conn = use_connection([])

    response = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": "2026-11-22",
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [{"id_empleado": 7}],
        },
    )

    assert response.status_code == 200
    assert conn.commits == 1
    cursor = conn.cursors[0]
    assert "::jsonb" in (cursor.query or "")
    assert json.loads(cursor.params[6]) == [{"id_tipo_residuo": 4, "peso_kg": 10.5}]
    assert json.loads(cursor.params[7]) == [{"id_empleado": 7}]


@pytest.mark.parametrize("rol", ["ADMIN", "SUPERVISOR"])
def test_lecturas_dashboard_permiten_admin_y_supervisor(
    client: TestClient,
    rol: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    correo = f"{rol.lower()}@ecohuancayo.pe"
    token = create_access_token(correo, {"rol": rol})
    catalogos = {
        "distritos": [],
        "cargos": [{"id": 1, "nombre": "Operador"}],
        "tipos_vehiculo": [{"id": 1, "nombre": "Camión"}],
        "tipos_residuo": [],
        "estados_recojo": [],
        "centros_reciclaje": [],
    }
    use_connection(
        [
            {
                "total_recojos": 1,
                "total_kg_reciclados": 10.0,
                "clientes_activos": 1,
                "vehiculos_disponibles": 1,
                "recojos_completados": 1,
                "recojos_pendientes": 0,
            }
        ],
        [{"tipo_residuo": "Papel", "total_kg": 10.0}],
        [
            {
                "id_cliente": 1,
                "razon_social": "Cliente Demo",
                "ruc": "20123456789",
                "estado": True,
                "total_registros": 1,
            }
        ],
        [
            {
                "id_empleado": 1,
                "nombres": "Ana",
                "apellidos": "Pérez",
                "dni": "70123456",
                "estado": True,
                "total_registros": 1,
            }
        ],
        [
            {
                "id_vehiculo": 1,
                "id_tipo_vehiculo": 1,
                "tipo_vehiculo": "Camión",
                "placa": "ABC-123",
                "capacidad_kg": 3500.0,
                "estado": "Disponible",
                "total_registros": 1,
            }
        ],
        [{"catalogos": catalogos}],
    )

    async def fallar(*args: Any, **kwargs: Any) -> Any:
        raise httpx.ConnectError("servicio caído")

    monkeypatch.setattr(httpx.AsyncClient, "get", fallar)
    headers = {"Authorization": f"Bearer {token}"}
    rutas = [
        "/api/v1/dashboard/indicadores",
        "/api/v1/dashboard/kg-por-tipo-residuo",
        "/api/v1/clientes",
        "/api/v1/empleados",
        "/api/v1/flota",
        "/api/v1/catalogos",
    ]

    for ruta in rutas:
        respuesta = client.get(ruta, headers=headers)
        assert respuesta.status_code == 200, ruta

    respuesta_dni = client.get("/api/v1/externo/dni/70123456", headers=headers)
    assert respuesta_dni.status_code == 200
    assert respuesta_dni.json()["manual"] is True


@pytest.mark.parametrize("rol", ["ADMIN", "SUPERVISOR"])
def test_registrar_empleado_permitido_para_gestion(
    client: TestClient,
    rol: str,
) -> None:
    correo = f"{rol.lower()}@ecohuancayo.pe"
    conn = use_connection([usuario(correo=correo, rol=rol)], [])
    token = create_access_token(correo, {"rol": rol})

    respuesta = client.post(
        "/api/v1/empleados",
        json={
            "nombres": "Ana",
            "apellidos": "Pérez",
            "dni": "70123456",
            "telefono": "998877665",
            "id_cargo": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert conn.cursors[1].query == "CALL sp_registrar_empleado(%s, %s, %s, %s, %s)"
    assert conn.cursors[1].params == (
        "Ana",
        "Pérez",
        "70123456",
        "998877665",
        2,
    )
    assert conn.commits == 1


@pytest.mark.parametrize("rol", ["ADMIN", "SUPERVISOR"])
def test_registrar_vehiculo_permitido_para_gestion(
    client: TestClient,
    rol: str,
) -> None:
    correo = f"{rol.lower()}@ecohuancayo.pe"
    conn = use_connection([usuario(correo=correo, rol=rol)], [])
    token = create_access_token(correo, {"rol": rol})

    respuesta = client.post(
        "/api/v1/flota",
        json={
            "id_tipo_vehiculo": 1,
            "placa": "ABC-123",
            "capacidad_kg": 3500,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert conn.cursors[1].query == "CALL sp_registrar_vehiculo(%s, %s, %s)"
    assert conn.cursors[1].params == (1, "ABC-123", 3500.0)
    assert conn.commits == 1


def test_registrar_empleado_rechaza_operador(client: TestClient) -> None:
    correo = "operador@ecohuancayo.pe"
    use_connection([usuario(correo=correo, rol="OPERADOR")])
    token = create_access_token(correo, {"rol": "OPERADOR"})

    respuesta = client.post(
        "/api/v1/empleados",
        json={
            "nombres": "Ana",
            "apellidos": "Pérez",
            "dni": "70123456",
            "id_cargo": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403
    assert (
        respuesta.json()["detail"]
        == "Se requieren permisos de administrador o supervisor"
    )


def test_clima_huancayo_usa_zona_horaria_peru(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captura: dict[str, Any] = {}

    async def falso_get(*args: Any, **kwargs: Any) -> httpx.Response:
        captura.update(kwargs["params"])
        return httpx.Response(
            200,
            request=httpx.Request("GET", "https://api.open-meteo.test/v1/forecast"),
            json={
                "timezone": "America/Lima",
                "utc_offset_seconds": -18000,
                "current": {"time": "2026-11-23T16:00"},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", falso_get)

    respuesta = asyncio.run(clima_huancayo())

    assert captura["timezone"] == "America/Lima"
    assert respuesta["manual"] is False
    assert respuesta["timezone"] == "America/Lima"
    assert respuesta["current"]["time"] == "2026-11-23T16:00"


def test_externo_fallback_manual(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fallar(*args: Any, **kwargs: Any) -> Any:
        raise httpx.ConnectError("servicio caído")

    monkeypatch.setattr(httpx.AsyncClient, "get", fallar)

    response = client.get("/api/v1/externo/dni/12345678")

    assert response.status_code == 200
    body = response.json()
    assert body["manual"] is True
    assert body["mensaje"]

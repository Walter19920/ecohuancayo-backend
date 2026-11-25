"""Pruebas básicas de la API con conexión de base de datos simulada.

Las variables de entorno se definen antes de importar la aplicación para que
``Settings`` no dependa de un ``.env`` real. ``get_db`` se reemplaza con una
conexión falsa mediante ``dependency_overrides``; así las pruebas no necesitan
PostgreSQL ni red.
"""

import asyncio
import json
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

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
os.environ["WEATHER_API_BASE_URL"] = "https://api.weatherapi.com/v1"
os.environ["WEATHER_API_KEY"] = "clave-de-prueba"
os.environ["HUANCAYO_LAT"] = "-12.0651"
os.environ["HUANCAYO_LON"] = "-75.2049"

from backend.core.database import get_db  # noqa: E402
from backend.core.security import (  # noqa: E402
    create_access_token,
    hash_password,
    verify_password,
)
from backend.main import app  # noqa: E402
from backend.services.externo_service import clima_huancayo  # noqa: E402
from backend.services.recojo_service import (  # noqa: E402
    MENSAJE_FECHA_PASADA,
    MENSAJE_HORA_PASADA,
)

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


def empleado_asignable(
    *,
    id_empleado: int = 7,
    estado: bool = True,
    cargo_actual: str = "Operario de Recolección",
) -> dict[str, Any]:
    return {
        "id_empleado": id_empleado,
        "nombres": "Ana",
        "apellidos": "Pérez",
        "cargo_actual": cargo_actual,
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
        "/api/v1/auth/cambiar-password",
        "/api/v1/auth/solicitar-contrasena",
        "/api/v1/usuarios",
        "/api/v1/usuarios/solicitudes-contrasena",
        "/api/v1/usuarios/solicitudes-contrasena/{id_solicitud}/atender",
        "/api/v1/clientes",
        "/api/v1/empleados",
        "/api/v1/empleados/{id_empleado}/recojos",
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
    conn = use_connection([empleado_asignable()], [])

    response = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [{"id_empleado": 7}],
        },
    )

    assert response.status_code == 200
    assert conn.commits == 1
    assert conn.cursors[0].query == "SELECT * FROM fn_listar_empleados()"
    cursor = conn.cursors[1]
    assert "::jsonb" in (cursor.query or "")
    assert json.loads(cursor.params[6]) == [{"id_tipo_residuo": 4, "cantidad_kg": 10.5}]
    assert json.loads(cursor.params[7]) == [
        {"id_empleado": 7, "descripcion": "Operario asignado"}
    ]


def test_registrar_recojo_normaliza_peso_kg_a_cantidad_kg(client: TestClient) -> None:
    conn = use_connection([empleado_asignable()], [])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [
                {"id_tipo_residuo": 3, "peso_kg": 1500},
                {"id_tipo_residuo": 5, "peso_kg": 0.25},
            ],
            "empleados": [{"id_empleado": 7}],
        },
    )

    assert respuesta.status_code == 200
    residuos_enviados = json.loads(conn.cursors[1].params[6])
    assert residuos_enviados == [
        {"id_tipo_residuo": 3, "cantidad_kg": 1500.0},
        {"id_tipo_residuo": 5, "cantidad_kg": 0.25},
    ]
    assert all(isinstance(item["cantidad_kg"], float) for item in residuos_enviados)
    assert all("peso_kg" not in item for item in residuos_enviados)
    assert conn.commits == 1


@pytest.mark.parametrize("descripcion_recibida", [None, "", "   "])
def test_registrar_recojo_con_descripcion_por_defecto_en_cada_empleado(
    client: TestClient,
    descripcion_recibida: str | None,
) -> None:
    conn = use_connection(
        [empleado_asignable(), empleado_asignable(id_empleado=8)],
        [],
    )
    empleados: list[dict[str, Any]] = [
        {"id_empleado": 7},
        {"id_empleado": 8},
    ]
    if descripcion_recibida is not None:
        empleados[0]["descripcion"] = descripcion_recibida

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 3, "peso_kg": 1500}],
            "empleados": empleados,
        },
    )

    assert respuesta.status_code == 200
    assert json.loads(conn.cursors[1].params[7]) == [
        {"id_empleado": 7, "descripcion": "Operario asignado"},
        {"id_empleado": 8, "descripcion": "Operario asignado"},
    ]
    assert conn.commits == 1


def test_registrar_recojo_conserva_descripcion_de_empleado(client: TestClient) -> None:
    conn = use_connection([empleado_asignable()], [])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 3, "peso_kg": 1500}],
            "empleados": [
                {"id_empleado": 7, "descripcion": "  Conductor de la unidad  "}
            ],
        },
    )

    assert respuesta.status_code == 200
    assert json.loads(conn.cursors[1].params[7]) == [
        {"id_empleado": 7, "descripcion": "Conductor de la unidad"}
    ]
    assert conn.commits == 1


@pytest.mark.parametrize("peso_kg", [0, -1, -0.5])
def test_registrar_recojo_rechaza_peso_no_positivo(
    client: TestClient,
    peso_kg: float,
) -> None:
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 3, "peso_kg": peso_kg}],
            "empleados": [{"id_empleado": 7}],
        },
    )

    assert respuesta.status_code == 422
    assert conn.cursors == []
    assert conn.commits == 0


def test_registrar_recojo_rechaza_fecha_pasada(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ahora = datetime(2026, 11, 24, 16, 6, 30, tzinfo=ZoneInfo("America/Lima"))
    monkeypatch.setattr(
        "backend.services.recojo_service._ahora_en_peru",
        lambda: ahora,
    )
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(ahora.date() - timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [],
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == MENSAJE_FECHA_PASADA
    assert conn.cursors == []
    assert conn.commits == 0


def test_registrar_recojo_rechaza_hora_pasada_hoy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ahora = datetime(2026, 11, 24, 16, 6, 30, tzinfo=ZoneInfo("America/Lima"))
    monkeypatch.setattr(
        "backend.services.recojo_service._ahora_en_peru",
        lambda: ahora,
    )
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(ahora.date()),
            "hora_recojo": "15:00:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [],
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == MENSAJE_HORA_PASADA
    assert conn.cursors == []
    assert conn.commits == 0


def test_registrar_recojo_rechaza_sin_empleados(client: TestClient) -> None:
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [],
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == ("Debe asignar al menos 1 empleado al recojo.")
    assert conn.cursors == []
    assert conn.commits == 0


def test_registrar_recojo_rechaza_mas_de_dos_empleados(client: TestClient) -> None:
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [
                {"id_empleado": 7},
                {"id_empleado": 8},
                {"id_empleado": 9},
            ],
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Máximo 2 empleados por recojo."
    assert conn.cursors == []
    assert conn.commits == 0


def test_registrar_recojo_acepta_dos_empleados(client: TestClient) -> None:
    conn = use_connection(
        [
            empleado_asignable(),
            empleado_asignable(
                id_empleado=8, cargo_actual="Conductor de Unidad Pesada"
            ),
        ],
        [],
    )

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": [{"id_empleado": 7}, {"id_empleado": 8}],
        },
    )

    assert respuesta.status_code == 200
    assert json.loads(conn.cursors[1].params[7]) == [
        {"id_empleado": 7, "descripcion": "Operario asignado"},
        {"id_empleado": 8, "descripcion": "Operario asignado"},
    ]
    assert conn.commits == 1


@pytest.mark.parametrize(
    "empleados, filas",
    [
        ([{"id_empleado": 7}], [empleado_asignable(estado=False)]),
        (
            [{"id_empleado": 7}],
            [empleado_asignable(cargo_actual="Supervisor Ambiental")],
        ),
        ([{"id_empleado": 99}], []),
    ],
)
def test_registrar_recojo_rechaza_empleado_no_operativo(
    client: TestClient,
    empleados: list[dict[str, int]],
    filas: list[dict[str, Any]],
) -> None:
    conn = use_connection(filas)

    respuesta = client.post(
        "/api/v1/recojos",
        json={
            "id_vehiculo": 1,
            "id_centro_reciclaje": 2,
            "id_cliente": 3,
            "id_estado_recojo": 1,
            "fecha_recojo": str(date.today() + timedelta(days=1)),
            "hora_recojo": "08:30:00",
            "residuos": [{"id_tipo_residuo": 4, "peso_kg": 10.5}],
            "empleados": empleados,
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "No se puede asignar un empleado inactivo o no operativo al recojo."
    )
    assert len(conn.cursors) == 1
    assert conn.cursors[0].query == "SELECT * FROM fn_listar_empleados()"
    assert conn.commits == 0


def test_registrar_cliente_rechaza_correo_interno(client: TestClient) -> None:
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/clientes",
        json={
            "razon_social": "Empresa SAC",
            "ruc": "20123456789",
            "direccion": "Av. Giraldez 123, Huancayo",
            "correo": "cliente@ecohuancayo.pe",
            "telefono": "998877665",
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "El correo @ecohuancayo.pe está reservado para usuarios internos."
    )
    assert conn.cursors == []
    assert conn.commits == 0


def test_registrar_cliente_rechaza_correo_de_otro_cliente(
    client: TestClient,
) -> None:
    conn = use_connection([{"id_cliente": 9, "correo": "duplicado@empresa.com"}])

    respuesta = client.post(
        "/api/v1/clientes",
        json={
            "razon_social": "Empresa SAC",
            "ruc": "20123456789",
            "direccion": "Av. Giraldez 123, Huancayo",
            "correo": "duplicado@empresa.com",
            "telefono": "998877665",
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El correo ya pertenece a otro cliente."
    assert len(conn.cursors) == 1
    assert conn.cursors[0].query == "SELECT * FROM fn_listar_clientes(%s)"
    assert conn.cursors[0].params == ("duplicado@empresa.com",)
    assert conn.commits == 0


def test_registrar_cliente_rechaza_correo_de_usuario(client: TestClient) -> None:
    conn = use_connection(
        [],
        [{"id_usuario": 2, "correo": "operador@otraempresa.com"}],
    )

    respuesta = client.post(
        "/api/v1/clientes",
        json={
            "razon_social": "Empresa SAC",
            "ruc": "20123456789",
            "direccion": "Av. Giraldez 123, Huancayo",
            "correo": "operador@otraempresa.com",
            "telefono": "998877665",
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "El correo ya pertenece a un usuario del sistema."
    )
    assert len(conn.cursors) == 2
    assert conn.cursors[1].query == "SELECT * FROM fn_listar_usuarios()"
    assert conn.commits == 0


def test_registrar_cliente_valido(client: TestClient) -> None:
    conn = use_connection([], [], [])

    respuesta = client.post(
        "/api/v1/clientes",
        json={
            "razon_social": "Empresa SAC",
            "ruc": "20123456789",
            "direccion": "Av. Giraldez 123, Huancayo",
            "correo": "nuevo@empresa.com",
            "telefono": "998877665",
        },
    )

    assert respuesta.status_code == 200
    assert conn.cursors[2].query == "CALL sp_registrar_cliente(%s, %s, %s, %s, %s)"
    assert conn.commits == 1


def test_actualizar_cliente_permite_su_propio_correo(client: TestClient) -> None:
    conn = use_connection(
        [{"id_cliente": 5, "correo": "mismo@empresa.com"}],
        [],
        [],
    )

    respuesta = client.put(
        "/api/v1/clientes/5",
        json={
            "razon_social": "Empresa SAC",
            "direccion": "Av. Giraldez 123, Huancayo",
            "correo": "mismo@empresa.com",
            "telefono": "998877665",
            "estado": True,
        },
    )

    assert respuesta.status_code == 200
    assert conn.cursors[2].query == (
        "CALL sp_actualizar_cliente(%s, %s, %s, %s, %s, %s)"
    )
    assert conn.commits == 1


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
    conn = use_connection([usuario(correo=correo, rol=rol)], [], [])
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
    assert conn.cursors[1].query == "SELECT * FROM fn_listar_empleados()"
    assert conn.cursors[2].query == "CALL sp_registrar_empleado(%s, %s, %s, %s, %s)"
    assert conn.cursors[2].params == (
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
    assert conn.cursors[1].query == (
        "CALL sp_registrar_vehiculo(%s::INT, %s::VARCHAR, %s::NUMERIC)"
    )
    assert conn.cursors[1].params == (1, "ABC-123", Decimal("3500"))
    assert isinstance(conn.cursors[1].params[2], Decimal)
    assert conn.commits == 1


@pytest.mark.parametrize(
    "capacidad_recibida, esperada",
    [
        (3500.75, Decimal("3500.75")),
        ("1500.25", Decimal("1500.25")),
    ],
)
def test_registrar_vehiculo_envia_capacidad_numerica_exacta(
    client: TestClient,
    capacidad_recibida: float | str,
    esperada: Decimal,
) -> None:
    token = create_access_token("admin@ecohuancayo.pe")
    conn = use_connection([usuario()], [])

    respuesta = client.post(
        "/api/v1/flota",
        json={
            "id_tipo_vehiculo": 8,
            "placa": "XYZ-987",
            "capacidad_kg": capacidad_recibida,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert conn.cursors[1].query == (
        "CALL sp_registrar_vehiculo(%s::INT, %s::VARCHAR, %s::NUMERIC)"
    )
    assert conn.cursors[1].params == (8, "XYZ-987", esperada)
    assert isinstance(conn.cursors[1].params[2], Decimal)
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


def test_clima_huancayo_weatherapi_contrato_frontend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captura: dict[str, Any] = {}

    async def falso_get(*args: Any, **kwargs: Any) -> httpx.Response:
        captura["url"] = next(arg for arg in args if isinstance(arg, str))
        captura["params"] = kwargs["params"]
        return httpx.Response(
            200,
            request=httpx.Request("GET", "https://api.weatherapi.com/v1/current.json"),
            json={
                "location": {"name": "Huancayo", "tz_id": "America/Lima"},
                "current": {
                    "last_updated": "2026-11-24 10:30",
                    "temp_c": 18.5,
                    "humidity": 65,
                    "wind_kph": 9.4,
                    "lang": "es",
                },
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", falso_get)

    respuesta = asyncio.run(clima_huancayo())

    assert captura["url"] == "https://api.weatherapi.com/v1/current.json"
    assert captura["params"] == {
        "key": "clave-de-prueba",
        "q": "-12.0651,-75.2049",
        "lang": "es",
    }
    assert respuesta["manual"] is False
    assert respuesta["current"] == {
        "temperature_2m": 18.5,
        "relative_humidity_2m": 65,
        "wind_speed_10m": 9.4,
        "time": "2026-11-24T10:30",
    }
    assert respuesta["current_units"] == {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "wind_speed_10m": "km/h",
    }
    assert respuesta["timezone"] == "America/Lima"
    assert respuesta["utc_offset_seconds"] == -18000


def test_clima_huancayo_sin_api_key_devuelve_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.externo_service.get_settings",
        lambda: SimpleNamespace(
            weather_api_key="",
            weather_api_base_url="https://api.weatherapi.com/v1",
            huancayo_lat=-12.0651,
            huancayo_lon=-75.2049,
        ),
    )

    async def no_llamar(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("No se debe llamar a WeatherAPI sin API key")

    monkeypatch.setattr(httpx.AsyncClient, "get", no_llamar)

    respuesta = asyncio.run(clima_huancayo())

    assert respuesta["manual"] is True
    assert "manualmente" in respuesta["mensaje"]


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


@pytest.mark.parametrize("rol", ["ADMIN", "SUPERVISOR"])
def test_actualizar_estado_vehiculo_permitido_para_gestion(
    client: TestClient,
    rol: str,
) -> None:
    correo = f"{rol.lower()}@ecohuancayo.pe"
    conn = use_connection([usuario(correo=correo, rol=rol)], [])
    token = create_access_token(correo, {"rol": rol})

    respuesta = client.patch(
        "/api/v1/flota/3/estado",
        json={"estado": "En Ruta"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert conn.cursors[1].query == "CALL sp_actualizar_estado_vehiculo(%s, %s)"
    assert conn.cursors[1].params == (3, "En Ruta")
    assert conn.commits == 1


def test_actualizar_estado_vehiculo_rechaza_estado_invalido(
    client: TestClient,
) -> None:
    token = create_access_token("admin@ecohuancayo.pe")
    conn = use_connection([usuario()])

    respuesta = client.patch(
        "/api/v1/flota/3/estado",
        json={"estado": "Activo"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "El estado del vehículo debe ser Disponible, En Ruta, Mantenimiento o Inactivo."
    )
    assert len(conn.cursors) == 1
    assert conn.commits == 0


def test_actualizar_estado_vehiculo_rechaza_operador(client: TestClient) -> None:
    correo = "operador@ecohuancayo.pe"
    use_connection([usuario(correo=correo, rol="OPERADOR")])
    token = create_access_token(correo, {"rol": "OPERADOR"})

    respuesta = client.patch(
        "/api/v1/flota/3/estado",
        json={"estado": "Disponible"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_registrar_vehiculo_rechaza_capacidad_menor_a_100(
    client: TestClient,
) -> None:
    token = create_access_token("admin@ecohuancayo.pe")
    conn = use_connection([usuario()])

    respuesta = client.post(
        "/api/v1/flota",
        json={"id_tipo_vehiculo": 1, "placa": "ABC-123", "capacidad_kg": 99},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "La capacidad del vehículo debe ser de al menos 100 kg."
    )
    assert len(conn.cursors) == 1
    assert conn.commits == 0


def test_registrar_usuario_rechaza_correo_fuera_del_dominio(
    client: TestClient,
) -> None:
    token = create_access_token("admin@ecohuancayo.pe")
    conn = use_connection([usuario()])

    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "id_empleado": 10,
            "correo": "usuario@empresa.com",
            "password": "Secreta123",
            "rol": "OPERADOR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "El correo del usuario debe terminar en @ecohuancayo.pe."
    )
    assert len(conn.cursors) == 1
    assert conn.commits == 0


def test_registrar_usuario_rechaza_correo_duplicado_de_usuario(
    client: TestClient,
) -> None:
    correo = "operador@ecohuancayo.pe"
    conn = use_connection([usuario()], [{"correo": correo}])
    token = create_access_token("admin@ecohuancayo.pe")

    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "id_empleado": 10,
            "correo": correo,
            "password": "Secreta123",
            "rol": "OPERADOR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "El correo ya pertenece a un usuario del sistema."
    )
    assert len(conn.cursors) == 2
    assert conn.cursors[1].query == "SELECT * FROM fn_listar_usuarios()"
    assert conn.commits == 0


def test_registrar_usuario_rechaza_correo_duplicado_de_cliente(
    client: TestClient,
) -> None:
    correo = "cliente@ecohuancayo.pe"
    conn = use_connection([usuario()], [], [{"correo": correo}])
    token = create_access_token("admin@ecohuancayo.pe")

    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "id_empleado": 10,
            "correo": correo,
            "password": "Secreta123",
            "rol": "OPERADOR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El correo ya pertenece a un cliente."
    assert len(conn.cursors) == 3
    assert conn.cursors[2].query == "SELECT * FROM fn_listar_clientes(%s)"
    assert conn.commits == 0


def test_registrar_usuario_valido(client: TestClient) -> None:
    correo = "nuevo@ecohuancayo.pe"
    conn = use_connection([usuario()], [], [], [])
    token = create_access_token("admin@ecohuancayo.pe")

    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "id_empleado": 10,
            "correo": correo,
            "password": "Secreta123",
            "rol": "OPERADOR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert conn.cursors[3].query == "CALL sp_registrar_usuario(%s, %s, %s, %s)"
    assert conn.cursors[3].params[1] == correo
    assert conn.commits == 1


@pytest.mark.parametrize(
    "estado, fecha_fin",
    [("Vigente", None), ("Finalizado", "2026-01-31")],
)
def test_historial_cargos_devuelve_estado_textual(
    client: TestClient,
    estado: str,
    fecha_fin: str | None,
) -> None:
    fila = {
        "id_empleado_cargo": 12,
        "nombre_cargo": "Operario de Recolección",
        "fecha_inicio": "2025-06-01",
        "fecha_fin": fecha_fin,
        "estado": estado,
    }
    conn = use_connection([fila])

    respuesta = client.get("/api/v1/empleados/5/historial")

    assert respuesta.status_code == 200
    assert respuesta.json() == [fila]
    assert conn.cursors[0].query == "SELECT * FROM fn_historial_cargos_empleado(%s)"
    assert conn.cursors[0].params == (5,)


def test_registrar_empleado_rechaza_dni_duplicado(client: TestClient) -> None:
    correo = "admin@ecohuancayo.pe"
    conn = use_connection(
        [usuario(correo=correo)],
        [{"id_empleado": 3, "dni": "70123456"}],
    )
    token = create_access_token(correo)

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

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == (
        "Ya existe un empleado registrado con ese DNI."
    )
    assert conn.cursors[1].query == "SELECT * FROM fn_listar_empleados()"
    assert len(conn.cursors) == 2
    assert conn.commits == 0


@pytest.mark.parametrize(
    "campo, valor, mensaje",
    [
        ("dni", "1234567a", "El DNI debe tener exactamente 8 dígitos."),
        (
            "nombres",
            "Ana 123",
            "Los nombres no pueden estar vacíos ni contener números.",
        ),
        (
            "apellidos",
            "Pérez 4",
            "Los apellidos no pueden estar vacíos ni contener números.",
        ),
    ],
)
def test_registrar_empleado_rechaza_datos_invalidos(
    client: TestClient,
    campo: str,
    valor: str,
    mensaje: str,
) -> None:
    correo = "admin@ecohuancayo.pe"
    conn = use_connection([usuario(correo=correo)], [])
    token = create_access_token(correo)
    payload = {
        "nombres": "Ana",
        "apellidos": "Pérez",
        "dni": "70123456",
        "telefono": "998877665",
        "id_cargo": 2,
        campo: valor,
    }

    respuesta = client.post(
        "/api/v1/empleados",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == mensaje
    assert conn.cursors[1].query == "SELECT * FROM fn_listar_empleados()"
    assert len(conn.cursors) == 2
    assert conn.commits == 0


def test_historial_recojos_empleado(client: TestClient) -> None:
    filas = [
        {
            "id_recojo": 7,
            "fecha_recojo": "2026-11-25",
            "hora_recojo": "08:30:00",
            "cliente": "Cliente Demo",
            "centro_reciclaje": "Planta Huancayo",
            "vehiculo_placa": "ABC-123",
            "rol_en_recojo": "Conductor de Unidad Pesada",
            "estado_recojo": "Programado",
            "total_kg": 125.5,
        },
        {
            "id_recojo": 4,
            "fecha_recojo": "2026-11-20",
            "hora_recojo": "15:00:00",
            "cliente": "Otro Cliente",
            "centro_reciclaje": "Planta Huancayo",
            "vehiculo_placa": "ABC-123",
            "rol_en_recojo": "Operario de Recolección",
            "estado_recojo": "Completado",
            "total_kg": 80.0,
        },
    ]
    conn = use_connection(filas)

    respuesta = client.get("/api/v1/empleados/5/recojos")

    assert respuesta.status_code == 200
    assert respuesta.json() == filas
    assert conn.cursors[0].query == ("SELECT * FROM fn_historial_recojos_empleado(%s)")
    assert conn.cursors[0].params == (5,)


def test_historial_recojos_empleado_sin_resultados(client: TestClient) -> None:
    conn = use_connection([])

    respuesta = client.get("/api/v1/empleados/9/recojos")

    assert respuesta.status_code == 200
    assert respuesta.json() == []
    assert conn.cursors[0].query == ("SELECT * FROM fn_historial_recojos_empleado(%s)")
    assert conn.cursors[0].params == (9,)


MENSAJE_GENERICO_SOLICITUD = (
    "Si el correo pertenece a una cuenta activa, se notificó al Administrador."
)


def test_solicitar_contrasena_es_publico_y_normaliza_correo(
    client: TestClient,
) -> None:
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/auth/solicitar-contrasena",
        json={"correo": "  Operador@EcoHuancayo.pe  "},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_GENERICO_SOLICITUD}
    assert conn.cursors[0].query == "CALL sp_solicitar_cambio_contrasena(%s)"
    assert conn.cursors[0].params == ("operador@ecohuancayo.pe",)
    assert conn.commits == 1


def test_solicitar_contrasena_oculta_fallos_de_base_de_datos(
    client: TestClient,
) -> None:
    class ConexionFallida(FakeConnection):
        def cursor(self, *args: Any, **kwargs: Any) -> FakeCursor:
            raise RuntimeError("fallo interno de base de datos")

    app.dependency_overrides[get_db] = lambda: ConexionFallida()

    respuesta = client.post(
        "/api/v1/auth/solicitar-contrasena",
        json={"correo": "operador@ecohuancayo.pe"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_GENERICO_SOLICITUD}


def test_solicitar_contrasena_rechaza_correo_invalido(client: TestClient) -> None:
    conn = use_connection([])

    respuesta = client.post(
        "/api/v1/auth/solicitar-contrasena",
        json={"correo": "correo-sin-dominio"},
    )

    assert respuesta.status_code == 422
    assert len(conn.cursors) == 0


def test_listar_solicitudes_contrasena_como_admin(client: TestClient) -> None:
    filas = [
        {
            "id_solicitud": 3,
            "id_usuario": 7,
            "nombre_completo": "Ana Pérez",
            "correo": "ana@ecohuancayo.pe",
            "rol": "OPERADOR",
            "fecha_solicitud": "2026-11-24T09:30:00",
        },
        {
            "id_solicitud": 4,
            "id_usuario": 8,
            "nombre_completo": "Bruno Díaz",
            "correo": "bruno@ecohuancayo.pe",
            "rol": "SUPERVISOR",
            "fecha_solicitud": "2026-11-24T10:15:00",
        },
        {
            "id_solicitud": 5,
            "id_usuario": 9,
            "nombre_completo": "Carla Rojas",
            "correo": "carla@ecohuancayo.pe",
            "rol": "ADMIN",
            "fecha_solicitud": "2026-11-24T11:00:00",
        },
    ]
    conn = use_connection([usuario()], filas)
    token = create_access_token("admin@ecohuancayo.pe")

    respuesta = client.get(
        "/api/v1/usuarios/solicitudes-contrasena",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [fila["rol"] for fila in cuerpo] == [
        "Operador",
        "Supervisor",
        "Administrador",
    ]
    assert cuerpo[0]["nombre_completo"] == "Ana Pérez"
    assert conn.cursors[1].query == ("SELECT * FROM fn_listar_solicitudes_contrasena()")


def test_listar_solicitudes_contrasena_rechaza_operador(
    client: TestClient,
) -> None:
    use_connection([usuario(rol="OPERADOR")])
    token = create_access_token("operador@ecohuancayo.pe")

    respuesta = client.get(
        "/api/v1/usuarios/solicitudes-contrasena",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_atender_solicitud_contrasena_como_admin(client: TestClient) -> None:
    conn = use_connection([usuario()], [])
    token = create_access_token("admin@ecohuancayo.pe")

    respuesta = client.patch(
        "/api/v1/usuarios/solicitudes-contrasena/7/atender",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": "Solicitud atendida correctamente"}
    assert conn.cursors[1].query == "CALL sp_atender_solicitud_contrasena(%s)"
    assert conn.cursors[1].params == (7,)
    assert conn.commits == 1


def test_atender_solicitud_contrasena_rechaza_operador(
    client: TestClient,
) -> None:
    use_connection([usuario(rol="OPERADOR")])
    token = create_access_token("operador@ecohuancayo.pe")

    respuesta = client.patch(
        "/api/v1/usuarios/solicitudes-contrasena/7/atender",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_cambiar_mi_password_valida_actual_y_llama_sp(
    client: TestClient,
) -> None:
    conn = use_connection([usuario()], [usuario()], [])
    token = create_access_token("admin@ecohuancayo.pe")
    nueva = "NuevaSegura123"

    respuesta = client.patch(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": PASSWORD, "nueva_password": nueva},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": "Contraseña actualizada correctamente"}
    assert conn.cursors[2].query == "CALL sp_cambiar_password_usuario(%s, %s)"
    assert conn.cursors[2].params[0] == 1
    assert verify_password(nueva, conn.cursors[2].params[1])
    assert conn.commits == 1


def test_cambiar_mi_password_rechaza_contraseña_actual_incorrecta(
    client: TestClient,
) -> None:
    conn = use_connection([usuario()], [usuario()])
    token = create_access_token("admin@ecohuancayo.pe")

    respuesta = client.patch(
        "/api/v1/auth/cambiar-password",
        json={
            "password_actual": "Incorrecta123",
            "nueva_password": "NuevaSegura123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "La contraseña actual es incorrecta."
    assert len(conn.cursors) == 2
    assert conn.commits == 0


def test_cambiar_mi_password_requiere_autenticacion(client: TestClient) -> None:
    use_connection()

    respuesta = client.patch(
        "/api/v1/auth/cambiar-password",
        json={
            "password_actual": PASSWORD,
            "nueva_password": "NuevaSegura123",
        },
    )

    assert respuesta.status_code == 401

# AGENTS.md — EcoHuancayo S.A.C. Backend

API REST en **FastAPI** para la gestión de recojo de residuos: autenticación, usuarios,
clientes, empleados, flota, catálogos, recojos, dashboard y consultas externas.

Stack: Python **3.13**, FastAPI, psycopg3 (`psycopg[binary,pool]`), PostgreSQL (Supabase),
python-jose, bcrypt, httpx, pydantic-settings. Gestor de dependencias: **uv**.

El contrato de base de datos y las variables de entorno están en `PRD.md`. Ese documento es
la fuente de verdad; este archivo define cómo se trabaja.

---

## Reglas no negociables

1. **Cero SQL crudo y cero nombres de tablas.**
   - La única interfaz hacia la base de datos son las **20 operaciones** listadas abajo
     (`SELECT * FROM fn_...` y `CALL sp_...`), documentadas con firma exacta en `PRD.md §B`.
   - Prohibido `INSERT`, `UPDATE`, `DELETE`, `SELECT` directo, DDL o cualquier referencia a
     una tabla interna en código, docstrings, comentarios, tests o logs.
   - Si una operación necesaria no existe entre las 20 firmas: **detente y pregunta**. No
     inventes SQL ni crees objetos nuevos en la base de datos.
2. **Capas**: `apis/*_router.py → services/*_service.py → repositories/*_repo.py`.
   - Routers: validan entrada/salida y dependencias; no acceden a la BD.
   - Services: reglas de negocio, orquestación y fallbacks.
   - Repositories: único lugar que ejecuta las 20 operaciones; sin lógica de negocio.
   - Schemas Pydantic en `schemas/*_schema.py` como frontera de la API.
3. **Driver**: `psycopg_pool.ConnectionPool` con `row_factory=dict_row`, leyendo
   `DATABASE_URL` del entorno. El pool se abre y cierra en el `lifespan` de `main.py`.
   Los repositorios hacen `commit()` después de cada `CALL`.
4. **CORS**: `CORSMiddleware` en `main.py` leyendo `CORS_ORIGINS` (lista separada por comas;
   incluye `localhost:5173`, `localhost:3000` y dominios de producción) con
   `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
5. **APIs externas**: `httpx.AsyncClient` con `timeout=5.0`, URL y token desde variables de
   entorno. Si la API falla o expira, se responde con fallback elegante `{"manual": true, ...}`
   en lugar de propagar el error.
6. **Seguridad**:
   - Contraseñas con `bcrypt.hashpw(..., bcrypt.gensalt(rounds=12))` → hash `$2b$12$...`.
     **No usar passlib.**
   - JWT con python-jose (`JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`).
   - Si el usuario tiene `estado = False` en el login: **HTTP 403**
     `"Usuario inactivo. Contacte al administrador"`.
   - Endpoints administrativos (`/api/v1/usuarios`, registro de empleados y de vehículos)
     protegidos con la dependencia `require_admin` (rol `ADMIN`).
7. **Errores**: capturar `psycopg.Error` y devolver
   `HTTPException(status_code=400, detail=<mensaje limpio del RAISE EXCEPTION>)`, usando
   `e.diag.message_primary` (con `str(e)` como respaldo si viene vacío). Nunca exponer stack
   traces, SQL ni detalles internos.
8. **Ejecución**: siempre `uv run uvicorn backend.main:app`. **NUNCA usar `--reload`.**
9. **Secretos**: solo variables de entorno. Nunca hardcodear credenciales, tokens ni URLs
   privadas; `.env` no se versiona (solo `.env.example` con placeholders).

---

## Las 20 operaciones permitidas

Inventario de referencia rápida. Firmas, parámetros y columnas de retorno: `PRD.md §B`.

**Auth / Usuarios**
- `fn_obtener_usuario_por_correo`
- `sp_registrar_usuario`
- `fn_listar_usuarios`
- `sp_cambiar_estado_usuario`
- `sp_cambiar_password_usuario`

**Clientes**
- `fn_listar_clientes`
- `sp_registrar_cliente`
- `sp_actualizar_cliente`

**Empleados / Flota / Catálogos**
- `fn_listar_empleados`
- `sp_registrar_empleado`
- `sp_asignar_cargo_empleado`
- `fn_historial_cargos_empleado`
- `fn_listar_vehiculos`
- `sp_registrar_vehiculo`
- `fn_listar_catalogos`

**Recojos / Dashboard**
- `fn_listar_recojos`
- `sp_registrar_recojo_completo`
- `sp_actualizar_estado_recojo`
- `fn_obtener_indicadores_dashboard`
- `fn_kg_por_tipo_residuo`

---

## Estructura del proyecto

```
Backend/
├── pyproject.toml
├── uv.lock
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── .github/workflows/ci.yml
├── src/backend/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── schemas/
│   │   ├── auth_schema.py
│   │   ├── usuario_schema.py
│   │   ├── cliente_schema.py
│   │   ├── empleado_schema.py
│   │   ├── flota_schema.py
│   │   ├── catalogo_schema.py
│   │   ├── recojo_schema.py
│   │   ├── dashboard_schema.py
│   │   └── externo_schema.py
│   ├── repositories/
│   │   ├── auth_repo.py
│   │   ├── usuario_repo.py
│   │   ├── cliente_repo.py
│   │   ├── empleado_repo.py
│   │   ├── flota_repo.py
│   │   ├── catalogo_repo.py
│   │   ├── recojo_repo.py
│   │   └── dashboard_repo.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── usuario_service.py
│   │   ├── cliente_service.py
│   │   ├── empleado_service.py
│   │   ├── flota_service.py
│   │   ├── catalogo_service.py
│   │   ├── recojo_service.py
│   │   ├── dashboard_service.py
│   │   └── externo_service.py
│   └── apis/
│       ├── auth_router.py
│       ├── usuario_router.py
│       ├── cliente_router.py
│       ├── empleado_router.py
│       ├── flota_router.py
│       ├── catalogo_router.py
│       ├── recojo_router.py
│       ├── dashboard_router.py
│       └── externo_router.py
└── tests/
    └── test_api.py
```

- El paquete importable es `backend` (src-layout). `uv sync` lo instala en editable, por eso
  `backend.main:app` resuelve sin `PYTHONPATH`.
- No crear archivos ni carpetas fuera de este árbol sin justificarlo.
- Los routers se montan bajo el prefijo `/api/v1`.

---

## Comandos

```bash
uv sync                                                     # instalar dependencias
uv add <paquete>                                            # dependencia de producción
uv add --dev <paquete>                                      # pytest, httpx, ruff
uv export --format requirements-txt --no-hashes --no-emit-project -o requirements.txt
uv run uvicorn backend.main:app                             # desarrollo (sin --reload)
uv run pytest tests/ -v                                     # toda la suite
uv run pytest tests/test_api.py::test_nombre -v             # un solo test
uv run ruff check . && uv run ruff format --check .         # lint + formato
```

Usar `uv export ... -o requirements.txt` en lugar de `>`: PowerShell escribe UTF-16/BOM y
rompe `pip install -r`.

Docker / Render:

```dockerfile
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Checklist antes de terminar un cambio

- [ ] `uv run pytest tests/ -v` en verde.
- [ ] `uv run ruff check .` sin errores.
- [ ] Sin nombres de tablas ni SQL crudo: solo las 20 operaciones de `PRD.md §B`.
- [ ] Sin secretos ni valores reales en el repo.
- [ ] Sin `--reload` en comandos, Dockerfile ni CI.
- [ ] Errores de BD devueltos como HTTP 400 con el mensaje limpio.

# PRD — EcoHuancayo S.A.C. Backend

API REST para la gestión integral de recojo de residuos: autenticación de usuarios,
clientes, empleados, flota, catálogos, recojos, dashboard de indicadores y consultas a
servicios externos (clima, RUC y DNI).

- **Stack**: Python 3.13 · FastAPI · psycopg3 (`psycopg[binary,pool]`) · PostgreSQL
  (Supabase) · python-jose · bcrypt · httpx · pydantic-settings.
- **Gestor de dependencias**: uv (src-layout, paquete `backend`).
- **Ejecución local**: `uv run uvicorn backend.main:app` (nunca `--reload`).
- **Contrato de BD**: exclusivamente las 20 operaciones de la sección B. No se permite SQL
  crudo ni referencias a tablas internas en ninguna capa del proyecto.

---

## A. Variables de entorno

Ningún valor real se versiona. `.env` está ignorado; solo se publica `.env.example` con
placeholders.

| Variable | Obligatoria | Descripción | Se usa en |
|---|---|---|---|
| `DATABASE_URL` | Sí | Cadena de conexión PostgreSQL (incluye credenciales) | `core/database.py` |
| `JWT_SECRET` | Sí | Clave de firma de los tokens JWT | `core/security.py` |
| `JWT_ALGORITHM` | Sí | Algoritmo de firma (p. ej. `HS256`) | `core/security.py` |
| `JWT_EXPIRE_MINUTES` | Sí | Vigencia del token en minutos | `core/security.py` |
| `CORS_ORIGINS` | Sí | Orígenes permitidos separados por coma | `main.py` |
| `APIS_PERU_TOKEN` | Sí | Token del proveedor de consultas RUC/DNI | `services/externo_service.py` |
| `APIS_PERU_BASE_URL` | Sí | URL base del proveedor RUC/DNI | `services/externo_service.py` |
| `OPEN_METEO_URL` | Sí | URL base de Open-Meteo | `services/externo_service.py` |
| `HUANCAYO_LAT` | Sí | Latitud de Huancayo | `services/externo_service.py` |
| `HUANCAYO_LON` | Sí | Longitud de Huancayo | `services/externo_service.py` |

Contenido de referencia para `.env.example` (solo placeholders):

```dotenv
DATABASE_URL=postgresql://<usuario>:<password>@<host>:<puerto>/<base_de_datos>
JWT_SECRET=<cadena_larga_aleatoria>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=<minutos>
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,<dominio_produccion>
APIS_PERU_TOKEN=<token>
APIS_PERU_BASE_URL=<url_base>
OPEN_METEO_URL=<url_base>
HUANCAYO_LAT=<latitud>
HUANCAYO_LON=<longitud>
```

---

## B. Contrato de PostgreSQL (ya creado en Supabase)

Estas 20 firmas son la **única interfaz** permitida hacia la base de datos. Nombres,
orden de parámetros y columnas de retorno son contrato inmutable: no se modifican desde
Python. Se ejecutan con `psycopg` (`dict_row`); los `CALL` requieren `commit()`.

### Auth / Usuarios

**Obtener usuario por correo**

```sql
SELECT * FROM fn_obtener_usuario_por_correo(%s)
```

- Parámetro: `p_correo`
- Retorna: `(id_usuario, id_empleado, correo, password_hash, nombre_completo, rol, estado)`

**Registrar usuario**

```sql
CALL sp_registrar_usuario(%s, %s, %s, %s)
```

- Parámetros: `p_id_empleado, p_correo, p_password_hash, p_rol`

**Listar usuarios**

```sql
SELECT * FROM fn_listar_usuarios()
```

- Retorna: `(id_usuario, id_empleado, nombre_completo, dni, correo, rol, estado, fecha_creacion)`

**Cambiar estado de usuario**

```sql
CALL sp_cambiar_estado_usuario(%s, %s)
```

- Parámetros: `p_id_usuario, p_estado`

**Cambiar contraseña de usuario**

```sql
CALL sp_cambiar_password_usuario(%s, %s)
```

- Parámetros: `p_id_usuario, p_nuevo_password_hash`

### Clientes

**Listar / buscar clientes**

```sql
SELECT * FROM fn_listar_clientes(%s)
```

- Parámetro: `p_busqueda`
- Retorna: `(id_cliente, razon_social, ruc, direccion, correo, telefono, estado)`

**Registrar cliente**

```sql
CALL sp_registrar_cliente(%s, %s, %s, %s, %s)
```

- Parámetros: `p_razon_social, p_ruc, p_direccion, p_correo, p_telefono`

**Actualizar cliente**

```sql
CALL sp_actualizar_cliente(%s, %s, %s, %s, %s, %s)
```

- Parámetros: `p_id_cliente, p_razon_social, p_direccion, p_correo, p_telefono, p_estado`

### Empleados / Flota / Catálogos

**Listar empleados**

```sql
SELECT * FROM fn_listar_empleados()
```

- Retorna: `(id_empleado, nombres, apellidos, dni, telefono, id_cargo_actual, cargo_actual, estado)`

**Registrar empleado**

```sql
CALL sp_registrar_empleado(%s, %s, %s, %s, %s)
```

- Parámetros: `p_nombres, p_apellidos, p_dni, p_telefono, p_id_cargo`

**Asignar cargo a empleado**

```sql
CALL sp_asignar_cargo_empleado(%s, %s)
```

- Parámetros: `p_id_empleado, p_id_cargo`

**Historial de cargos de un empleado**

```sql
SELECT * FROM fn_historial_cargos_empleado(%s)
```

- Parámetro: `p_id_empleado`
- Retorna: `(id_empleado_cargo, nombre_cargo, fecha_inicio, fecha_fin, estado)`

**Listar vehículos**

```sql
SELECT * FROM fn_listar_vehiculos()
```

- Retorna: `(id_vehiculo, id_tipo_vehiculo, tipo_vehiculo, placa, capacidad_kg, estado)`

**Registrar vehículo**

```sql
CALL sp_registrar_vehiculo(%s, %s, %s)
```

- Parámetros: `p_id_tipo_vehiculo, p_placa, p_capacidad_kg`

**Listar catálogos**

```sql
SELECT fn_listar_catalogos() AS catalogos
```

- Retorna: JSONB con las claves `distritos`, `cargos`, `tipos_vehiculo`, `tipos_residuo`,
  `estados_recojo`, `centros_reciclaje`.

### Recojos / Dashboard

**Listar recojos**

```sql
SELECT * FROM fn_listar_recojos(%s)
```

- Parámetro: `p_id_estado`
- Retorna: `(id_recojo, cliente, ruc, centro_reciclaje, distrito_destino, vehiculo_placa, id_estado_recojo, estado_recojo, fecha_recojo, hora_recojo, total_kg)`

**Registrar recojo completo**

```sql
CALL sp_registrar_recojo_completo(%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
```

- Parámetros: `p_id_vehiculo, p_id_centro_reciclaje, p_id_cliente, p_id_estado_recojo, p_fecha_recojo, p_hora_recojo, p_residuos, p_empleados`
- `p_residuos` y `p_empleados` se envían serializados como JSON y se castean a `jsonb`.

**Actualizar estado de recojo**

```sql
CALL sp_actualizar_estado_recojo(%s, %s)
```

- Parámetros: `p_id_recojo, p_id_estado_recojo`

**Indicadores del dashboard**

```sql
SELECT * FROM fn_obtener_indicadores_dashboard()
```

- Retorna: `(total_recojos, total_kg_reciclados, clientes_activos, vehiculos_disponibles, recojos_completados, recojos_pendientes)`

**Kilogramos por tipo de residuo**

```sql
SELECT * FROM fn_kg_por_tipo_residuo()
```

- Retorna: `(tipo_residuo, total_kg)`

---

## C. Integración de APIs externas

Implementación en `src/backend/services/externo_service.py`, expuesta por
`src/backend/apis/externo_router.py`. Todas usan `httpx.AsyncClient` con `timeout=5.0` y
configuración desde variables de entorno.

| Endpoint | Consume | Variables | Fallback si falla |
|---|---|---|---|
| `GET /api/v1/externo/clima-huancayo` | Open-Meteo | `OPEN_METEO_URL`, `HUANCAYO_LAT`, `HUANCAYO_LON` | `{"manual": true, ...}` |
| `GET /api/v1/externo/ruc/{ruc}` | Consulta SUNAT (proveedor externo) | `APIS_PERU_BASE_URL`, `APIS_PERU_TOKEN` | `{"manual": true, ...}` |
| `GET /api/v1/externo/dni/{dni}` | Consulta RENIEC (proveedor externo) | `APIS_PERU_BASE_URL`, `APIS_PERU_TOKEN` | `{"manual": true, ...}` |

Reglas:

- El fallback devuelve HTTP 200 con `manual: true` y un mensaje para captura manual; no se
  propaga la excepción del proveedor.
- Nunca registrar el token ni la URL completa con credenciales en logs.

---

## D. CI/CD y despliegue

### Integración continua — `.github/workflows/ci.yml`

- Se ejecuta en cada `push` y `pull_request`.
- Pasos: instalar dependencias (`requirements.txt`), `ruff check .`, `pytest tests/ -v`.
- `DATABASE_URL` y el resto de variables se inyectan desde **GitHub Secrets** (solo nombres,
  nunca valores en el repositorio).
- Los tests no deben depender de una base real: usar `dependency_overrides` o mocks. Si el
  secret no está disponible, la suite debe seguir pasando.

### Dockerfile para Render

- Imagen base `python:3.13-slim`.
- Instalar primero `requirements.txt` (solo dependencias de terceros) para aprovechar el
  caché de capas de Docker.
- Después copiar `pyproject.toml` y `src/`; el paquete `backend` no queda instalado por
  `requirements.txt`, así que arrancar con `ENV PYTHONPATH=/app/src` (alternativa:
  `pip install --no-cache-dir --no-deps -e .`).
- Exponer el puerto 8000.
- `requirements.txt` incluye también las dependencias de desarrollo (pytest, ruff) por
  decisión del proyecto; para una imagen mínima exportar con `--no-dev`.
- Comando de arranque:

```dockerfile
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- Sin `--reload` en ningún entorno.
- Si Render exige el puerto dinámico, usar como alternativa
  `CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]`.

---

## E. Supuestos y fuera de alcance

- No se crean tablas, migraciones, triggers ni funciones/procedimientos: el esquema ya
  existe en Supabase y solo se consume mediante las 20 operaciones de la sección B.
- No se usa ORM (SQLAlchemy, Django ORM ni similar).
- No hay nombres de tablas internas en el repositorio; si una operación no está cubierta por
  el contrato, el desarrollo se detiene y se consulta.
- El frontend (React/Vite) es un proyecto separado; aquí solo se habilita CORS.
- `requirements.txt` se genera con
  `uv export --format requirements-txt --no-hashes --no-emit-project -o requirements.txt` y se
  versiona. No incluye `-e .`: solo dependencias de terceros.

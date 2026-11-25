# EcoHuancayo S.A.C. — Backend



API y lógica de negocio de EcoHuancayo para la gestión operativa de clientes, rutas, flota, residuos y recojos en Huancayo, junto con integraciones externas y control de calidad automatizado.



---



## Estructura del proyecto



```text

Backend/

├── .github/                  # Workflows de automatización e integración continua (GitHub Actions)

├── .pytest_cache/            # Caché interna generada por pytest

├── .ruff_cache/              # Caché interna generada por Ruff

├── .venv/                    # Entorno virtual local de Python

├── src/

│   └── backend/

│       ├── apis/             # Endpoints HTTP y recepción de peticiones del cliente

│       ├── core/             # Configuración central, variables de entorno, seguridad y utilidades base

│       ├── repositories/     # Acceso y consultas a datos / persistencia

│       ├── schemas/          # Modelos de validación para entrada y salida de datos

│       ├── services/         # Lógica de negocio, reglas operativas y consultas externas

│       ├── __init__.py       # Inicialización del paquete del backend

│       └── main.py           # Punto de entrada de la aplicación y registro de rutas/módulos

├── tests/                    # Pruebas automatizadas con pytest para endpoints, servicios e integraciones

├── .dockerignore             # Archivos y carpetas excluidos al construir la imagen de Docker

├── .env                      # Variables de entorno locales (no exponer secretos)

├── .gitignore                # Archivos ignorados por Git

├── .python-version           # Versión de Python configurada para el entorno

├── AGENTS.md                 # Lineamientos y convenciones de trabajo para agentes/desarrollo

├── Dockerfile                # Definición del contenedor para empaquetar y desplegar el servicio

├── PRD.md                    # Documento de requisitos y especificaciones del producto/backend

├── pyproject.toml            # Configuración del proyecto, herramientas y dependencias

├── README.md                 # Documentación general del repositorio backend

├── requirements.txt          # Lista de dependencias de Python

└── uv.lock                   # Archivo de bloqueo de dependencias gestionadas con uv

```



---



## Integraciones externas



- APIsPeru (externo_service.py / externo_router.py): Consulta DNI para validación en registro de empleados y RUC para validación de datos de clientes usando APIS_PERU_BASE_URL y APIS_PERU_TOKEN.

- Weather API (externo_service.py): Consulta el clima actual de Huancayo usando WEATHER_API_BASE_URL y WEATHER_API_KEY, adaptando la respuesta al contrato esperado con zona horaria America/Lima.

- Manejo de llamadas y respaldo (fallback): Las consultas se ejecutan de forma asíncrona con httpx.AsyncClient y timeout de 5 segundos. Si el proveedor falla o falta configuración, se devuelve manual: true para completar los datos de forma manual sin detener la operación.



---



## Instalación y trabajo en local



1. Clonar el repositorio:

   git clone https://github.com/Walter19920/ecohuancayo-backend.git

   cd ecohuancayo-backend



2. Configurar el archivo .env con las variables necesarias (como APIS_PERU_BASE_URL, APIS_PERU_TOKEN, WEATHER_API_BASE_URL, WEATHER_API_KEY, base de datos y parámetros de ubicación según corresponda).



3. Instalar dependencias:

   - Con uv (recomendado por pyproject.toml y uv.lock):

     uv sync

   - O con entorno virtual y pip:

     python -m venv .venv

     pip install -r requirements.txt



4. Ejecutar la aplicación y pruebas en local según el comando de tu entorno (y pytest para correr la suite de pruebas).



---



## Despliegue y CI/CD



- Web Service en Docker (Región Oregon): El backend se despliega como servicio web continuo para mantener procesos activos y atender peticiones en todo momento. Está empaquetado con Dockerfile para asegurar paridad entre desarrollo y producción sin fallos de dependencias, y ubicado en Oregon para mantener estabilidad y buena conexión con la base de datos y APIs externas.

- GitHub Actions: Automatiza la validación del código en cada cambio mediante pipelines (ejecutando pruebas con pytest y verificaciones) para detectar errores o regresiones antes de llegar a producción.
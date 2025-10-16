# TMF Translation Middleware (Flask)

This service bridges TMF APIs and a Django-based inventory application. It:
- Loads the native Django OpenAPI schema at startup (from NATIVE_SCHEMA_URL or local fallback)
- Translates TMF requests to the native format and native responses back to TMF (stubs)
- Generates and exposes a TMF-like resource catalogue derived from the native schema
- Performs simple runtime validation of TMF request/response payloads
- Proxies CRUD requests to the Django inventory app

Container: FlaskTMFTranslationMiddleware
Type: backend (Flask)

Docs: /docs
OpenAPI: /openapi.json

## Project structure

- FlaskTMFTranslationMiddleware/
  - app/
    - __init__.py (Flask app factory, OpenAPI docs, CORS, startup schema load)
    - main.py (entrypoint, runs on port 3001 by default)
    - config.py (environment-driven config)
    - routes/
      - health.py (/)
      - catalogue.py (/tmf/catalogue)
      - tmf_proxy.py (/tmf/<resource> CRUD)
      - validate.py (/validate)
    - services/
      - schema_loader.py (load schema from URL/local, in-memory cache)
      - translator.py (TMF/native translation stubs)
      - validator.py (jsonschema-based validation)
      - catalogue.py (derive catalogue from schema)
      - proxy.py (forward requests to Django)
    - utils/
      - logging.py
      - errors.py
  - schema/native_openapi.json (local fallback schema)
  - .env.example
  - requirements.txt
  - run.py (delegates to app.main)

## Requirements

- Python 3.10+
- pip

## Installation

```bash
cd tmfmapperv1-5116-5210/FlaskTMFTranslationMiddleware
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit as needed
```

## Configuration

Environment variables (see .env.example):
- DJANGO_BASE_URL: Base URL to the Django inventory app (default: http://localhost:8000)
- NATIVE_SCHEMA_URL: URL to fetch the OpenAPI schema (optional). If empty or fails, fallback to schema/native_openapi.json
- SERVICE_PORT: Port to run the Flask app (default: 3001)
- LOG_LEVEL: Logging level (INFO, DEBUG, etc.)

NOTE: Do not commit real secrets. Request any sensitive values from the orchestrator so they are set in the environment.

## Running

```bash
python run.py
# or
python -m app.main
```

The app will listen on 0.0.0.0:3001 by default. Open API docs at /docs.

## Endpoints

- GET / 
  - Health: { "status": "ok", "service": "TMF Translation Middleware" }
- GET /config
  - Current non-sensitive configuration and schema load status
- GET /tmf/catalogue
  - Generated TMF-like resource catalogue derived from the native schema
- GET/POST /tmf/<resource>
  - CRUD collection stubs proxied to Django (translation stubs applied)
- GET/PATCH/PUT/DELETE /tmf/<resource>/<id>
  - CRUD item stubs proxied to Django (translation stubs applied)
- POST /validate
  - Validate a payload against a derived schema for a resource
  - Request:
    {
      "resource": "resourceName",
      "payload": { ... },
      "direction": "tmf_to_native" | "native_to_tmf"
    }

## How it works

- Startup
  - app/__init__.py uses SchemaLoader to fetch the native OpenAPI schema from NATIVE_SCHEMA_URL with a 10s timeout.
  - If not provided or fails, it loads schema/native_openapi.json as a fallback.
  - The schema is cached in memory and can be reloaded via SchemaLoader.reload() in future enhancements.

- Translation
  - app/services/translator.py defines tmf_to_native and native_to_tmf stubs.
  - TODO markers indicate where to implement detailed TMF mapping rules per resource.

- Validation
  - app/services/validator.py performs simple jsonschema-based validation by deriving a schema from components/schemas.
  - This is minimal and should be extended for TMF-specific contracts.

- Catalogue
  - app/services/catalogue.py builds a simplified catalogue of resources and fields from components/schemas in the native OpenAPI.

- Proxy
  - app/services/proxy.py forwards CRUD requests to the Django app at DJANGO_BASE_URL.
  - If upstream is unavailable or errors, endpoints return HTTP 502 with context.

## Security and future work

- Secure upstream communication: add auth headers or mTLS per Django app requirements.
- Dynamic schema evolution: call app.schema_loader.reload() when schema changes; add admin route if needed.
- Enhance validation to TMF-specific rules.
- Implement full TMF mapping rules in translator.py using the native model semantics.

## Troubleshooting

- 502 UpstreamUnavailable: Ensure DJANGO_BASE_URL is reachable.
- No catalogue or validation schemas: Ensure NATIVE_SCHEMA_URL returns OpenAPI JSON or provide a valid local fallback in schema/native_openapi.json.
- Change port: Set SERVICE_PORT in the environment.

## License

Internal project middleware component.

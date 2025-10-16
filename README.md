# TMF Translation Middleware (Flask)

This service bridges TMF APIs and a Django-based inventory application. It:
- Loads the native Django OpenAPI schema at startup (from NATIVE_OPENAPI_URL/NATIVE_OPENAPI_PATH or legacy NATIVE_SCHEMA_URL, else bundled fallback)
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
  - schema/native_openapi.json (bundled fallback schema)
  - schema/native_openapi_sample.json (richer sample to test catalogue generation)
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
- NATIVE_OPENAPI_URL: URL to a provided native OpenAPI schema (highest priority)
- NATIVE_OPENAPI_PATH: Local filesystem path to a provided native OpenAPI schema (used if set; takes precedence over bundled fallback)
- NATIVE_SCHEMA_URL: Legacy URL variable still supported (lower priority than NATIVE_OPENAPI_URL)
- SERVICE_PORT: Port to run the Flask app (default: 3001)
- LOG_LEVEL: Logging level (INFO, DEBUG, etc.)
- VALIDATE_REQUESTS: Enable pre-proxy validation for TMF requests (default false)
- VALIDATE_RESPONSES: Enable post-proxy validation for TMF responses (default false)
- ENABLE_METRICS: Enable /metrics endpoint and counters (default true)
- UPSTREAM_TIMEOUT_SECONDS: Upstream proxy timeout in seconds (default 10)
- UPSTREAM_RETRY_COUNT: Number of retry attempts for upstream requests (default 1)
- UPSTREAM_AUTH_BEARER: Static bearer token to send to upstream (optional)
- UPSTREAM_API_KEY: Static API key to send to upstream (optional)
- UPSTREAM_API_KEY_HEADER: Header name for API key (default X-API-Key)

Load order priority:
1) NATIVE_OPENAPI_PATH (if set and readable)
2) NATIVE_OPENAPI_URL (or legacy NATIVE_SCHEMA_URL)
3) Bundled fallback at schema/native_openapi.json

NOTE: Do not commit real secrets. Request any sensitive values from the orchestrator so they are set in the environment.

## Running

```bash
python run.py
# or
python -m app.main
```

The app will listen on 0.0.0.0:3001 by default. Open API docs at /docs.

## Providing a schema and viewing the catalogue

Option A: Provide schema via URL
- Set NATIVE_OPENAPI_URL=https://example.com/native_openapi.json
- Start the app
- Visit GET /tmf/catalogue to see the generated TMF-style catalogue

Option B: Provide schema via local file path
- Place your OpenAPI JSON somewhere accessible to the app (e.g., mount into container)
- Set NATIVE_OPENAPI_PATH to that absolute path
- Start the app
- Visit GET /tmf/catalogue

Option C: Use the bundled sample
- No env var needed. The app falls back to schema/native_openapi.json
- For a richer example, set NATIVE_OPENAPI_PATH to schema/native_openapi_sample.json

The /tmf/catalogue response contains:
- resource: Name of the resource (from components/schemas)
- description: Schema description if present
- keyAttributes: Heuristic key attributes (id and/or required fields)
- attributes: All attributes with type and required flag
- capabilities: Inferred CRUD booleans when detectable from OpenAPI paths
- generatedFromSchema: Metadata including OpenAPI version, source used, and timestamp

## Endpoints

- GET /
  - Health: { "status": "ok", "service": "TMF Translation Middleware" }
- GET /config
  - Current non-sensitive configuration and schema load status
- GET /tmf/catalogue
  - Generated TMF-style resource catalogue derived from the native OpenAPI
- GET/POST /tmf/<resource>
  - CRUD collection stubs proxied to Django (translation applied); supports query mapping
- GET/PATCH/PUT/DELETE /tmf/<resource>/<id>
  - CRUD item stubs proxied to Django (translation applied)
- POST /validate
  - Validate a payload against a derived schema for a resource
  - Request:
    {
      "resource": "resourceName",
      "payload": { ... },
      "direction": "tmf_to_native" | "native_to_tmf"
    }
- Admin
  - POST /admin/schema/reload -> force reload schema (uses ETag/Last-Modified if available)
  - GET /admin/schema/info -> schema source metadata and component list
  - GET /admin/upstream/health -> upstream base URL reachability
- Observability
  - GET /metrics -> basic counters and latency aggregates (enable via ENABLE_METRICS=true)

## How it works

- Startup
  - app/__init__.py builds the SchemaLoader with prioritized URL/path and bundled fallback.
  - SchemaLoader tries local path (if provided), then URL, then bundled file.
  - The schema is cached in memory and can be reloaded via SchemaLoader.reload().

- Translation
  - app/services/translator.py defines tmf_to_native and native_to_tmf; includes a sample mapping for Item and pass-through for unmapped fields. Query param mapping supported.

- Validation
  - app/services/validator.py performs simple jsonschema-based validation by deriving a schema from components/schemas. Direction-aware hooks exist for request vs response. Toggle via VALIDATE_REQUESTS/VALIDATE_RESPONSES or ?validate=true on calls.

- Catalogue
  - app/services/catalogue.py builds a TMF-style catalogue including attributes, key attributes, and inferred CRUD capabilities.

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
- No catalogue or validation schemas: Ensure schema is reachable via NATIVE_OPENAPI_URL/NATIVE_SCHEMA_URL or set NATIVE_OPENAPI_PATH, otherwise bundled fallback is used.
- Change port: Set SERVICE_PORT in the environment.
- Inspect loaded config and schema status: GET /config

## License

Internal project middleware component.

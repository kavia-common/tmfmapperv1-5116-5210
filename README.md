# TMF Translation Middleware (Flask)

This middleware bridges TMF APIs and a Django-based inventory application.

It dynamically loads the native Django OpenAPI schema, translates TMF-formatted requests to the native format and vice versa for responses, exposes a TMF-style catalogue derived from the schema, validates payloads at runtime, and proxies CRUD requests to the upstream Django service. It emits structured logs, propagates request IDs, and serves basic metrics.

Container: FlaskTMFTranslationMiddleware
Type: backend (Flask)
Docs UI: /docs

## Overview and architecture

At startup the Flask app:
- Loads configuration from environment via app/config.py.
- Configures CORS, structured logging, and observability middleware that injects and propagates a request ID and measures request duration.
- Initializes a SchemaLoader that loads the upstream native OpenAPI schema from one of: NATIVE_OPENAPI_URL, legacy NATIVE_SCHEMA_URL, or NATIVE_OPENAPI_PATH; if none succeed it falls back to the bundled schema/native_openapi.json.
- Registers blueprints for health, TMF proxy CRUD, validation, catalogue, admin utilities, and metrics (conditionally).
- Serves Swagger UI under /docs via flask-smorest.

High-level components:
- app/services/schema_loader.py handles schema retrieval, in-memory caching, and conditional HTTP caching (ETag/Last-Modified) on reloads.
- app/services/translator.py defines a simple registry for resource field mappings and supports both body and query parameter translation.
- app/services/validator.py performs jsonschema validation using the loaded OpenAPI components and applies direction-aware hooks.
- app/services/proxy.py forwards HTTP requests to the upstream Django service with timeout, retries, and configurable auth headers.
- app/observability/middleware.py injects request IDs and logs request_start/request_end entries.
- app/observability/metrics.py counts total requests, proxy errors, validation failures, and aggregates latency distribution.
- app/routes/* expose API endpoints.

### Sequence flow (simplified)
1. Client calls a TMF endpoint under /tmf.
2. Translator converts TMF query/body to native.
3. Proxy forwards to Django with propagated Authorization or configured auth.
4. Response is translated back to TMF and optionally validated.
5. Metrics and logs are recorded; request ID is returned in X-Request-ID.

## Quick start

- Requirements: Python 3.10+, pip
- Setup:

```bash
cd tmfmapperv1-5116-5210/FlaskTMFTranslationMiddleware
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# optionally prepare env
# cp .env.example .env  # if you create one
```

- Run:

```bash
python run.py
# or
python -m app.main
```

- Default port: 3001 (0.0.0.0). Visit:
  - /docs for Swagger UI
  - / for health
  - /config for effective non-sensitive config
  - /tmf/catalogue for the generated catalogue

## Configuration (env vars) with defaults and examples

The application reads environment variables via app/config.py. Defaults are shown in parentheses.

- DJANGO_BASE_URL (http://localhost:8000)
  Upstream Django base URL. Example: https://django-app.internal

- NATIVE_OPENAPI_URL ("")
  Direct URL to a native OpenAPI JSON. Takes precedence over legacy NATIVE_SCHEMA_URL.

- NATIVE_SCHEMA_URL ("")
  Legacy name for a native OpenAPI URL. Used if NATIVE_OPENAPI_URL is not provided.

- NATIVE_OPENAPI_PATH ("")
  Local file path to a native OpenAPI JSON. If set and readable it is preferred over bundled fallback. Example: /app/schema/native_openapi_sample.json

- SERVICE_PORT (3001)
  Port to bind Flask.

- LOG_LEVEL ("INFO")
  Logging verbosity: DEBUG, INFO, WARNING, ERROR.

- VALIDATE_REQUESTS ("false")
  Pre-proxy validation of TMF requests. Accepts 1/true/yes/on.

- VALIDATE_RESPONSES ("false")
  Post-proxy validation of translated responses. Accepts 1/true/yes/on.

- ENABLE_METRICS ("true")
  Enables /metrics endpoint.

- UPSTREAM_TIMEOUT_SECONDS (10)
  Timeout for upstream requests in seconds. Float accepted.

- UPSTREAM_RETRY_COUNT (1)
  Number of retries on upstream errors.

- UPSTREAM_AUTH_BEARER ("")
  Static bearer token value to send upstream. If set, Authorization: Bearer <token> is added.

- UPSTREAM_API_KEY ("")
  Static API key value to send upstream.

- UPSTREAM_API_KEY_HEADER ("X-API-Key")
  Header name for API key if UPSTREAM_API_KEY is provided.

Schema source priority:
1) NATIVE_OPENAPI_URL (or NATIVE_SCHEMA_URL for legacy)
2) NATIVE_OPENAPI_PATH (if explicitly provided and readable)
3) Bundled fallback: schema/native_openapi.json

Note: Do not commit secrets. Populate sensitive values at runtime via environment or secret manager.

## Endpoints

- Health
  - GET /
    Returns {"status":"ok","service":"TMF Translation Middleware"}.

- Config
  - GET /config
    Returns effective non-sensitive configuration and whether the schema is currently loaded.

- TMF proxy CRUD
  - GET /tmf/<resource>
    Translates query params, proxies to upstream e.g., GET /<resource>.
  - POST /tmf/<resource>
    Optionally validates TMF payload, translates to native, proxies to upstream.
  - GET /tmf/<resource>/<id>
    Proxies to upstream item endpoint and translates response to TMF.
  - PATCH|PUT /tmf/<resource>/<id>
    Optionally validates TMF payload, translates, proxies, and translates response back.
  - DELETE /tmf/<resource>/<id>
    Proxies delete and returns translated upstream response.

  Validation toggle per request:
  - Query param ?validate=true|false overrides VALIDATE_REQUESTS/VALIDATE_RESPONSES.

- Validation
  - POST /validate
    Body:
    {
      "resource": "ResourceName",
      "payload": { ... },
      "direction": "tmf_to_native" | "native_to_tmf"
    }
    Returns { "valid": bool, "errors": [] }.

- Catalogue
  - GET /tmf/catalogue
    Generates TMF-style catalogue from OpenAPI components/schemas and inferred CRUD capabilities.

- Admin
  - POST /admin/schema/reload
    Reloads schema. If using URL, employs ETag/Last-Modified for conditional fetch.
  - GET /admin/schema/info
    Returns schema source metadata and list of component schema names.
  - GET /admin/upstream/health
    Probes DJANGO_BASE_URL reachability.

- Metrics
  - GET /metrics
    Returns counters (total_requests, proxy_errors, validation_failures) and latency aggregates (count, avg, max, min). Controlled by ENABLE_METRICS.

## Translator mapping registry: how to add resource mappings (sample Item)

Translations live in app/services/translator.py. A simple in-memory registry maps resource names to field mappings and optional hooks:

Example registry entry (already present for "Item"):
```python
self.registry = {
    "Item": {
        "tmf_to_native": {
            "id": "id",
            "name": "name",
            "quantity": "quantity",
        },
        "native_to_tmf": {
            "id": "id",
            "name": "name",
            "quantity": "quantity",
        },
        "tmf_post": self._item_tmf_post,     # optional post-translate hook for requests
        "native_post": self._item_native_post, # optional post-translate hook for responses
        "query": { "id": "id", "name": "name" } # query param mapping
    }
}
```

To add a new resource mapping, for example "Warehouse":
```python
self.registry["Warehouse"] = {
    "tmf_to_native": {
        "id": "id",
        "location": "location",
        "capacity": "capacity",
    },
    "native_to_tmf": {
        "id": "id",
        "location": "location",
        "capacity": "capacity",
    },
    "query": {
        "id": "id",
        "location": "location",
    }
}
```

Behavior details:
- Unmapped fields are passed through by default so you can iteratively refine mappings.
- Query params are translated via translate_query_params using the "query" sub-map.
- Optional post-processing hooks can normalize or enrich payloads after mapping. Provided examples ensure id normalization.

## Validation toggles and direction-aware validation

Validation is performed by app/services/validator.py using jsonschema Draft7 over schemas derived from OpenAPI components:
- For "tmf_to_native" direction (requests), the TMF request body is validated before translating/proxying when VALIDATE_REQUESTS is enabled or ?validate=true is set.
- For "native_to_tmf" direction (responses), the translated TMF response is validated after receiving upstream data when VALIDATE_RESPONSES is enabled or ?validate=true is set.
- The validator locates a matching component schema by case-insensitive name or title; it falls back to a generic object schema if none is found.
- Responses on validation failure return a consistent error shape with code "ValidationFailed" and increment the validation_failures counter.

Per-request override:
- Add ?validate=true to force validation on a specific call, or ?validate=false to disable it regardless of global flags.

## Observability: request IDs, structured logging, metrics

- Request ID propagation:
  - If the client sends X-Request-ID, it is used; otherwise a UUID is generated.
  - X-Request-ID is echoed back in responses and included in logged request_start and request_end lines.

- Structured logs:
  - app/observability/middleware.py logs request_start and request_end with method, path, status, duration_ms, and request_id.
  - Global errors return a consistent JSON body containing error.code, error.message, and trace_id.

- Metrics (/metrics):
  - Counters: total_requests, proxy_errors, validation_failures.
  - Latency aggregates: count, avg, max, min in milliseconds.
  - Metrics are collected in-memory and exposed as JSON. The endpoint is enabled only when ENABLE_METRICS=true.

## Upstream Django integration

- Base URL:
  - Configure DJANGO_BASE_URL to the root of the Django app. Example: https://django-app.internal

- Health expectations:
  - Admin endpoint GET /admin/upstream/health performs a simple GET to DJANGO_BASE_URL and returns ok plus HTTP status if reachable.

- Auth header behavior:
  - Incoming Authorization header is forwarded to the upstream by default.
  - If UPSTREAM_AUTH_BEARER is set, the ProxyService injects Authorization: Bearer <token> on all upstream requests. If both are present, forwarded headers are merged with static auth; static bearer can overwrite Authorization if provided in both places.
  - If UPSTREAM_API_KEY is set, the header defined by UPSTREAM_API_KEY_HEADER (default X-API-Key) is added to all upstream requests.
  - If the client supplies the same API key header, it is forwarded by the proxy as well.

- Timeouts and retries:
  - UPSTREAM_TIMEOUT_SECONDS controls the request timeout.
  - UPSTREAM_RETRY_COUNT controls simple retry attempts with a small backoff.

## Troubleshooting

- Upstream timeouts or 502 UpstreamUnavailable:
  - Verify DJANGO_BASE_URL is correct and reachable from the middleware environment.
  - Increase UPSTREAM_TIMEOUT_SECONDS or UPSTREAM_RETRY_COUNT if the upstream is slow or transiently failing.
  - Use GET /admin/upstream/health to quickly test connectivity.

- Schema reload issues:
  - Use POST /admin/schema/reload to force a reload. If using a URL source, ETag/Last-Modified headers are honored. Check GET /admin/schema/info for source metadata and lastLoadedAt.
  - If NATIVE_OPENAPI_PATH is set, ensure the file is mounted and readable by the process.
  - When no schema is available, the service falls back to an empty minimal schema; catalogue and validation will be limited.

- Validation failures:
  - Inspect the "errors" array in the response for precise jsonschema paths and messages.
  - Confirm that your "resource" name matches the component schema key or title in the upstream OpenAPI (case-insensitive).
  - Use ?validate=false on specific proxy calls if needed to bypass strict validation temporarily.

- Authorization header forwarding:
  - Ensure clients send Authorization or configure UPSTREAM_AUTH_BEARER.
  - If using API keys, confirm UPSTREAM_API_KEY and UPSTREAM_API_KEY_HEADER are set consistently on both middleware and upstream.

- Port and binding:
  - Set SERVICE_PORT to change the listener port. The app binds to 0.0.0.0 for container use.

## Future improvements

- Enrich translator mapping with full TMF semantics and nested/array field handling.
- Expand validator with direction-specific adjustments (e.g., handle writeOnly/readOnly, partial updates).
- Provide per-resource configuration files or a pluggable registry mechanism.
- Export Prometheus-compatible metrics and tracing (OpenTelemetry) instead of JSON-only metrics.
- Harden error handling and add circuit breaking for upstream instability.
- Add pagination and filtering helpers for query translation.

## Project structure

- FlaskTMFTranslationMiddleware/
  - app/
    - __init__.py (Flask app factory, CORS, docs, startup schema load, metrics middleware)
    - main.py (entrypoint)
    - config.py (environment-driven config and defaults)
    - routes/
      - health.py (/)
      - catalogue.py (/tmf/catalogue)
      - tmf_proxy.py (/tmf/<resource>, /tmf/<resource>/<id>)
      - validate.py (/validate)
      - admin.py (/admin/*)
    - services/
      - schema_loader.py (URL/local load, conditional caching, reload)
      - translator.py (mapping registry and query translation)
      - validator.py (jsonschema-based validation)
      - catalogue.py (derive catalogue from OpenAPI)
      - proxy.py (forward to Django with timeout/retries/auth)
    - observability/
      - middleware.py (request ID propagation, structured logs)
      - metrics.py (counters and latency aggregates)
    - utils/
      - logging.py (log configuration)
      - errors.py (consistent error shape)
  - schema/native_openapi.json (bundled fallback)
  - schema/native_openapi_sample.json (richer example)
  - requirements.txt
  - run.py

## Running

```bash
python run.py
# or
python -m app.main
```

The app will listen on 0.0.0.0:3001 by default. Swagger UI is available at /docs.

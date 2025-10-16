import os

class Config:
    """
    Application configuration using environment variables.

    DJANGO_BASE_URL: Base URL for Django inventory app (e.g., https://django-app.internal)
    NATIVE_SCHEMA_URL: URL to fetch native OpenAPI schema from Django app; fallback to local file if missing or fails
    NATIVE_OPENAPI_URL: Optional - direct URL to a provided native OpenAPI schema (takes precedence over NATIVE_SCHEMA_URL)
    NATIVE_OPENAPI_PATH: Optional - local filesystem path to a provided native OpenAPI schema
    SERVICE_PORT: Port for Flask app (defaults to 3001)
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    VALIDATE_REQUESTS/RESPONSES: Enable runtime validation in proxy pre/post stages (default false)
    ENABLE_METRICS: Enable metrics endpoint and counters
    UPSTREAM_TIMEOUT_SECONDS: Timeout for upstream Django requests
    UPSTREAM_RETRY_COUNT: Simple retry count for upstream
    UPSTREAM_AUTH_BEARER: Static bearer token to send to upstream (optional)
    UPSTREAM_API_KEY: Static API key value to send to upstream (optional)
    UPSTREAM_API_KEY_HEADER: Header name for API key (default X-API-Key)
    """

    def __call__(self):
        # Allows Flask to call this object as a config source
        return self

    DJANGO_BASE_URL = os.getenv("DJANGO_BASE_URL", "http://localhost:8000")
    # Backwards compatibility (legacy var)
    NATIVE_SCHEMA_URL = os.getenv("NATIVE_SCHEMA_URL", "")
    # New variables for explicit control
    NATIVE_OPENAPI_URL = os.getenv("NATIVE_OPENAPI_URL", "")
    NATIVE_OPENAPI_PATH = os.getenv("NATIVE_OPENAPI_PATH", "")
    SERVICE_PORT = int(os.getenv("SERVICE_PORT", "3001"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Validation toggles
    VALIDATE_REQUESTS = os.getenv("VALIDATE_REQUESTS", "false").lower() in ("1", "true", "yes", "on")
    VALIDATE_RESPONSES = os.getenv("VALIDATE_RESPONSES", "false").lower() in ("1", "true", "yes", "on")

    # Observability / Metrics
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() in ("1", "true", "yes", "on")

    # Proxy config
    UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "10"))
    UPSTREAM_RETRY_COUNT = int(os.getenv("UPSTREAM_RETRY_COUNT", "1"))
    UPSTREAM_AUTH_BEARER = os.getenv("UPSTREAM_AUTH_BEARER", "")
    UPSTREAM_API_KEY = os.getenv("UPSTREAM_API_KEY", "")
    UPSTREAM_API_KEY_HEADER = os.getenv("UPSTREAM_API_KEY_HEADER", "X-API-Key")

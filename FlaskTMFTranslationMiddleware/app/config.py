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

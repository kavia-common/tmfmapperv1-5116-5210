import os
import time
from flask import Flask, jsonify, g
from flask_cors import CORS
from flask_smorest import Api
from .config import Config
from .utils.logging import configure_logging
from .utils.errors import register_error_handlers
from .services.schema_loader import SchemaLoader
from .observability.middleware import register_observability_middleware
from .observability.metrics import blp as metrics_blp, record_request_metrics

# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.
    
    This sets up:
    - Config via environment variables with sensible defaults
    - CORS for all routes
    - OpenAPI/Swagger via flask-smorest
    - Global schema loader to load the native Django OpenAPI schema at startup
    - Route blueprints for health, config, catalogue, TMF proxy, validation, admin, and metrics
    - Observability middleware with request ID propagation and basic metrics
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # Configure app from environment
    app.config.from_object(Config())

    # Logging
    configure_logging(app.config.get("LOG_LEVEL", "INFO"))

    # CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Observability middleware (request id + timing)
    register_observability_middleware(app)

    # OpenAPI / Swagger UI
    app.config["API_TITLE"] = "TMF Translation Middleware API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    api = Api(app)

    # Determine schema source priority: NATIVE_OPENAPI_URL > NATIVE_OPENAPI_PATH > NATIVE_SCHEMA_URL (legacy) > bundled file
    provided_url = app.config.get("NATIVE_OPENAPI_URL") or app.config.get("NATIVE_SCHEMA_URL") or ""
    provided_path = app.config.get("NATIVE_OPENAPI_PATH") or ""
    bundled_path = os.path.join(os.path.dirname(__file__), "..", "schema", "native_openapi.json")
    local_path = provided_path if provided_path else bundled_path

    # Load native schema at startup with graceful fallback
    schema_loader = SchemaLoader(
        url=provided_url,
        local_path=local_path,
        session=None,
    )
    app.schema_loader = schema_loader
    try:
        schema_loader.load_schema()
        app.logger.info("Native schema loaded successfully")
    except Exception as exc:
        app.logger.warning(f"Failed to load native schema on startup: {exc}")

    # Register routes
    from .routes.health import blp as health_blp
    from .routes.catalogue import blp as catalogue_blp
    from .routes.tmf_proxy import blp as tmf_blp
    from .routes.validate import blp as validate_blp
    from .routes.admin import blp as admin_blp

    api.register_blueprint(health_blp)
    api.register_blueprint(catalogue_blp)
    api.register_blueprint(tmf_blp)
    api.register_blueprint(validate_blp)
    api.register_blueprint(admin_blp)
    if app.config.get("ENABLE_METRICS", True):
        api.register_blueprint(metrics_blp)

    # Config endpoint (simple, not via smorest for quick inspection)
    @app.get("/config")
    def get_config():
        """
        Returns effective runtime configuration (non-sensitive).
        """
        return jsonify({
            "DJANGO_BASE_URL": app.config.get("DJANGO_BASE_URL"),
            "NATIVE_SCHEMA_URL": app.config.get("NATIVE_SCHEMA_URL"),
            "NATIVE_OPENAPI_URL": app.config.get("NATIVE_OPENAPI_URL"),
            "NATIVE_OPENAPI_PATH": app.config.get("NATIVE_OPENAPI_PATH"),
            "SERVICE_PORT": app.config.get("SERVICE_PORT"),
            "LOG_LEVEL": app.config.get("LOG_LEVEL"),
            "VALIDATE_REQUESTS": app.config.get("VALIDATE_REQUESTS"),
            "VALIDATE_RESPONSES": app.config.get("VALIDATE_RESPONSES"),
            "ENABLE_METRICS": app.config.get("ENABLE_METRICS"),
            "UPSTREAM_TIMEOUT_SECONDS": app.config.get("UPSTREAM_TIMEOUT_SECONDS"),
            "UPSTREAM_RETRY_COUNT": app.config.get("UPSTREAM_RETRY_COUNT"),
            "schema_loaded": app.schema_loader.schema is not None
        })

    # Error handlers
    register_error_handlers(app)

    # Per-request metrics capture
    @app.before_request
    def _metrics_start():
        g._request_metrics_start = time.time()

    @app.after_request
    def _metrics_end(response):
        try:
            record_request_metrics(getattr(g, "_request_metrics_start", time.time()))
        except Exception:
            pass
        return response

    return app

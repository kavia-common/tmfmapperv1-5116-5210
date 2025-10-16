import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api
from .config import Config
from .utils.logging import configure_logging
from .utils.errors import register_error_handlers
from .services.schema_loader import SchemaLoader

# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.
    
    This sets up:
    - Config via environment variables with sensible defaults
    - CORS for all routes
    - OpenAPI/Swagger via flask-smorest
    - Global schema loader to load the native Django OpenAPI schema at startup
    - Route blueprints for health, config, catalogue, TMF proxy, and validation
    
    Returns:
        A configured Flask app instance.
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # Configure app from environment
    app.config.from_object(Config())

    # Logging
    configure_logging(app.config.get("LOG_LEVEL", "INFO"))

    # CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    # OpenAPI / Swagger UI
    app.config["API_TITLE"] = "TMF Translation Middleware API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    api = Api(app)

    # Load native schema at startup with graceful fallback
    schema_loader = SchemaLoader(
        url=app.config.get("NATIVE_SCHEMA_URL"),
        local_path=os.path.join(os.path.dirname(__file__), "..", "schema", "native_openapi.json"),
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

    api.register_blueprint(health_blp)
    api.register_blueprint(catalogue_blp)
    api.register_blueprint(tmf_blp)
    api.register_blueprint(validate_blp)

    # Config endpoint (simple, not via smorest for quick inspection)
    @app.get("/config")
    def get_config():
        """
        Returns effective runtime configuration (non-sensitive).
        """
        return jsonify({
            "DJANGO_BASE_URL": app.config.get("DJANGO_BASE_URL"),
            "NATIVE_SCHEMA_URL": app.config.get("NATIVE_SCHEMA_URL"),
            "SERVICE_PORT": app.config.get("SERVICE_PORT"),
            "LOG_LEVEL": app.config.get("LOG_LEVEL"),
            "schema_loaded": app.schema_loader.schema is not None
        })

    # Error handlers
    register_error_handlers(app)

    return app

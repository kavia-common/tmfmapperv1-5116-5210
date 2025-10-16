from flask_smorest import Blueprint
from flask.views import MethodView
from flask import current_app, jsonify
from app.services.proxy import ProxyService

blp = Blueprint("Admin", "admin", url_prefix="/admin", description="Administrative endpoints")

# PUBLIC_INTERFACE
@blp.route("/schema/reload", methods=["POST"])
class SchemaReload(MethodView):
    """Reload the native OpenAPI schema with conditional HTTP caching."""
    def post(self):
        app = current_app
        schema = app.schema_loader.reload()
        return jsonify({"status": "reloaded", "source": app.schema_loader.source_info(), "openapi": schema.get("openapi")})

# PUBLIC_INTERFACE
@blp.route("/schema/info", methods=["GET"])
class SchemaInfo(MethodView):
    """Return details about the currently loaded schema source and status."""
    def get(self):
        app = current_app
        schema = app.schema_loader.get_schema()
        return jsonify({"source": app.schema_loader.source_info(), "openapi": schema.get("openapi"), "components": list((schema.get("components", {}).get("schemas", {}) or {}).keys())})

# PUBLIC_INTERFACE
@blp.route("/upstream/health", methods=["GET"])
class UpstreamHealth(MethodView):
    """Check health of the upstream Django service."""
    def get(self):
        app = current_app
        proxy = ProxyService(
            base_url=app.config.get("DJANGO_BASE_URL"),
            timeout_seconds=app.config.get("UPSTREAM_TIMEOUT_SECONDS", 10.0),
            retry_count=0,
            static_bearer=app.config.get("UPSTREAM_AUTH_BEARER", ""),
            api_key=app.config.get("UPSTREAM_API_KEY", ""),
            api_key_header=app.config.get("UPSTREAM_API_KEY_HEADER", "X-API-Key"),
        )
        ok, status = proxy.health()
        return jsonify({"ok": ok, "status": status, "baseUrl": app.config.get("DJANGO_BASE_URL")}), (200 if ok else 502)

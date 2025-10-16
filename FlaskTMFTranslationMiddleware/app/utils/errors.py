from flask import jsonify, request
import uuid

class UpstreamUnavailableError(Exception):
    """Raised when the upstream Django service is unavailable."""

def _trace_id() -> str:
    # Use X-Request-ID if present else generate new
    return request.headers.get("X-Request-ID") or request.environ.get("request_id") or str(uuid.uuid4())

def _error_response(code: str, message: str, status: int = 500, details=None):
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "trace_id": _trace_id(),
    }
    return jsonify(body), status

def register_error_handlers(app):
    """
    Register global error handlers for the Flask app. Ensures consistent error shape.
    """
    @app.errorhandler(UpstreamUnavailableError)
    def handle_upstream_unavailable(err: UpstreamUnavailableError):
        return _error_response("UpstreamUnavailable", str(err), 502)

    @app.errorhandler(404)
    def handle_404(err):
        return _error_response("NotFound", "Resource not found", 404)

    @app.errorhandler(400)
    def handle_400(err):
        return _error_response("BadRequest", "Invalid request", 400)

    @app.errorhandler(500)
    def handle_500(err):
        return _error_response("InternalServerError", "An unexpected error occurred", 500)

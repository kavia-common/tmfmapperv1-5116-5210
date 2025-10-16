from flask import jsonify

class UpstreamUnavailableError(Exception):
    """Raised when the upstream Django service is unavailable."""

def register_error_handlers(app):
    """
    Register global error handlers for the Flask app.
    """
    @app.errorhandler(UpstreamUnavailableError)
    def handle_upstream_unavailable(err: UpstreamUnavailableError):
        return jsonify({"error": "UpstreamUnavailable", "message": str(err)}), 502

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"error": "NotFound", "message": "Resource not found"}), 404

    @app.errorhandler(500)
    def handle_500(err):
        return jsonify({"error": "InternalServerError", "message": "An unexpected error occurred"}), 500

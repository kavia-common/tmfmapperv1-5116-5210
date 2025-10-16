from flask_smorest import Blueprint
from flask.views import MethodView

blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")

# PUBLIC_INTERFACE
@blp.route("/", methods=["GET"])
class HealthCheck(MethodView):
    """Health check endpoint."""
    def get(self):
        """Returns service health."""
        return {"status": "ok", "service": "TMF Translation Middleware"}

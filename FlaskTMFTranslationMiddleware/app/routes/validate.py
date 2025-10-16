from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request, jsonify, current_app
from app.services.validator import ValidationService

blp = Blueprint("Validation", "validation", url_prefix="/", description="Runtime validation endpoints")

# PUBLIC_INTERFACE
@blp.route("/validate", methods=["POST"])
class Validate(MethodView):
    """
    Validate a payload against the loaded native schema for the given resource.
    Request JSON:
    {
      "resource": "resourceName",
      "payload": { ... },
      "direction": "tmf_to_native" | "native_to_tmf"
    }
    """
    def post(self):
        data = request.get_json(silent=True) or {}
        resource = data.get("resource")
        payload = data.get("payload")
        direction = data.get("direction", "tmf_to_native")

        service = ValidationService(current_app.schema_loader)

        valid, errors = service.validate(resource, payload, direction=direction)
        return jsonify({"valid": valid, "errors": errors})

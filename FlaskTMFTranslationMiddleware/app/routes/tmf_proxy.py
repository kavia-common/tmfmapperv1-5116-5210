from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request, jsonify, current_app
from app.services.translator import TranslatorService
from app.services.proxy import ProxyService
from app.utils.errors import UpstreamUnavailableError

blp = Blueprint("TMF Proxy", "tmf_proxy", url_prefix="/tmf", description="TMF CRUD proxy endpoints")

def _services():
    app = current_app
    translator = TranslatorService(app.schema_loader)
    proxy = ProxyService(base_url=app.config.get("DJANGO_BASE_URL"))
    return translator, proxy

# PUBLIC_INTERFACE
@blp.route("/<string:resource>", methods=["GET", "POST"])
class TMFResourceCollection(MethodView):
    """
    Collection endpoints for TMF resources.
    - GET: list resources
    - POST: create resource
    """
    def get(self, resource: str):
        translator, proxy = _services()
        # Translate TMF query params to native as needed (stub)
        native_query = translator.tmf_to_native(resource, request.args.to_dict())
        try:
            data, status = proxy.forward("GET", f"/{resource}", params=native_query)
        except UpstreamUnavailableError as e:
            return jsonify({"error": "Upstream unavailable", "detail": str(e)}), 502
        # Translate native list response back to TMF (stub)
        tmf_payload = translator.native_to_tmf(resource, data)
        return jsonify(tmf_payload), status

    def post(self, resource: str):
        translator, proxy = _services()
        tmf_payload = request.get_json(silent=True) or {}
        native_payload = translator.tmf_to_native(resource, tmf_payload)
        try:
            data, status = proxy.forward("POST", f"/{resource}", json=native_payload)
        except UpstreamUnavailableError as e:
            return jsonify({"error": "Upstream unavailable", "detail": str(e)}), 502
        tmf_response = translator.native_to_tmf(resource, data)
        return jsonify(tmf_response), status

# PUBLIC_INTERFACE
@blp.route("/<string:resource>/<string:item_id>", methods=["GET", "PATCH", "PUT", "DELETE"])
class TMFResourceItem(MethodView):
    """
    Item endpoints for TMF resources.
    """
    def get(self, resource: str, item_id: str):
        translator, proxy = _services()
        try:
            data, status = proxy.forward("GET", f"/{resource}/{item_id}")
        except UpstreamUnavailableError as e:
            return jsonify({"error": "Upstream unavailable", "detail": str(e)}), 502
        tmf_payload = translator.native_to_tmf(resource, data)
        return jsonify(tmf_payload), status

    def patch(self, resource: str, item_id: str):
        translator, proxy = _services()
        tmf_payload = request.get_json(silent=True) or {}
        native_payload = translator.tmf_to_native(resource, tmf_payload)
        try:
            data, status = proxy.forward("PATCH", f"/{resource}/{item_id}", json=native_payload)
        except UpstreamUnavailableError as e:
            return jsonify({"error": "Upstream unavailable", "detail": str(e)}), 502
        tmf_response = translator.native_to_tmf(resource, data)
        return jsonify(tmf_response), status

    def put(self, resource: str, item_id: str):
        translator, proxy = _services()
        tmf_payload = request.get_json(silent=True) or {}
        native_payload = translator.tmf_to_native(resource, tmf_payload)
        try:
            data, status = proxy.forward("PUT", f"/{resource}/{item_id}", json=native_payload)
        except UpstreamUnavailableError as e:
            return jsonify({"error": "Upstream unavailable", "detail": str(e)}), 502
        tmf_response = translator.native_to_tmf(resource, data)
        return jsonify(tmf_response), status

    def delete(self, resource: str, item_id: str):
        translator, proxy = _services()
        try:
            data, status = proxy.forward("DELETE", f"/{resource}/{item_id}")
        except UpstreamUnavailableError as e:
            return jsonify({"error": "Upstream unavailable", "detail": str(e)}), 502
        tmf_response = translator.native_to_tmf(resource, data)
        return jsonify(tmf_response), status

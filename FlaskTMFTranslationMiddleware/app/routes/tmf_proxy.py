from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request, jsonify, current_app
from app.services.translator import TranslatorService
from app.services.proxy import ProxyService
from app.services.validator import ValidationService
from app.utils.errors import UpstreamUnavailableError
from app.observability.metrics import inc_counter

blp = Blueprint("TMF Proxy", "tmf_proxy", url_prefix="/tmf", description="TMF CRUD proxy endpoints")

def _services():
    app = current_app
    translator = TranslatorService(app.schema_loader)
    proxy = ProxyService(
        base_url=app.config.get("DJANGO_BASE_URL"),
        timeout_seconds=app.config.get("UPSTREAM_TIMEOUT_SECONDS", 10.0),
        retry_count=app.config.get("UPSTREAM_RETRY_COUNT", 1),
        static_bearer=app.config.get("UPSTREAM_AUTH_BEARER", ""),
        api_key=app.config.get("UPSTREAM_API_KEY", ""),
        api_key_header=app.config.get("UPSTREAM_API_KEY_HEADER", "X-API-Key"),
    )
    validator = ValidationService(app.schema_loader)
    return translator, proxy, validator

def _should_validate(flag_name: str) -> bool:
    # allow query param override (?validate=true/false)
    qp = request.args.get("validate")
    if qp is not None:
        return qp.lower() in ("1", "true", "yes", "on")
    return current_app.config.get(flag_name, False)

def _error(code: str, message: str, status: int = 400):
    # keep consistent shape as errors.register_error_handlers
    from app.utils.errors import _error_response
    return _error_response(code, message, status)

# PUBLIC_INTERFACE
@blp.route("/<string:resource>", methods=["GET", "POST"])
class TMFResourceCollection(MethodView):
    """
    Collection endpoints for TMF resources.
    - GET: list resources
    - POST: create resource
    """
    def get(self, resource: str):
        translator, proxy, validator = _services()
        # Translate TMF query params to native
        native_query = translator.translate_query_params(resource, request.args.to_dict())
        try:
            data, status = proxy.forward("GET", f"/{resource}", params=native_query, headers=_forward_auth_headers())
        except UpstreamUnavailableError as e:
            inc_counter("proxy_errors")
            return _error("UpstreamUnavailable", str(e), 502)
        # Optional post validation
        tmf_payload = translator.native_to_tmf(resource, data)
        if _should_validate("VALIDATE_RESPONSES"):
            valid, errs = validator.validate(resource, tmf_payload.get("data"), direction="native_to_tmf")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Response payload failed validation", 502 if status < 500 else status)
        return jsonify(tmf_payload), status

    def post(self, resource: str):
        translator, proxy, validator = _services()
        tmf_payload = request.get_json(silent=True) or {}
        # Optional pre-validation on TMF request
        if _should_validate("VALIDATE_REQUESTS"):
            valid, errs = validator.validate(resource, tmf_payload, direction="tmf_to_native")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Request payload failed validation", 400)
        native_payload = translator.tmf_to_native(resource, tmf_payload)
        try:
            data, status = proxy.forward("POST", f"/{resource}", json=native_payload, headers=_forward_auth_headers())
        except UpstreamUnavailableError as e:
            inc_counter("proxy_errors")
            return _error("UpstreamUnavailable", str(e), 502)
        tmf_response = translator.native_to_tmf(resource, data)
        if _should_validate("VALIDATE_RESPONSES"):
            valid, errs = validator.validate(resource, tmf_response.get("data"), direction="native_to_tmf")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Response payload failed validation", 502 if status < 500 else status)
        return jsonify(tmf_response), status

# PUBLIC_INTERFACE
@blp.route("/<string:resource>/<string:item_id>", methods=["GET", "PATCH", "PUT", "DELETE"])
class TMFResourceItem(MethodView):
    """
    Item endpoints for TMF resources.
    """
    def get(self, resource: str, item_id: str):
        translator, proxy, validator = _services()
        try:
            data, status = proxy.forward("GET", f"/{resource}/{item_id}", headers=_forward_auth_headers())
        except UpstreamUnavailableError as e:
            inc_counter("proxy_errors")
            return _error("UpstreamUnavailable", str(e), 502)
        tmf_payload = translator.native_to_tmf(resource, data)
        if _should_validate("VALIDATE_RESPONSES"):
            valid, errs = validator.validate(resource, tmf_payload.get("data"), direction="native_to_tmf")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Response payload failed validation", 502 if status < 500 else status)
        return jsonify(tmf_payload), status

    def patch(self, resource: str, item_id: str):
        translator, proxy, validator = _services()
        tmf_payload = request.get_json(silent=True) or {}
        if _should_validate("VALIDATE_REQUESTS"):
            valid, errs = validator.validate(resource, tmf_payload, direction="tmf_to_native")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Request payload failed validation", 400)
        native_payload = translator.tmf_to_native(resource, tmf_payload)
        try:
            data, status = proxy.forward("PATCH", f"/{resource}/{item_id}", json=native_payload, headers=_forward_auth_headers())
        except UpstreamUnavailableError as e:
            inc_counter("proxy_errors")
            return _error("UpstreamUnavailable", str(e), 502)
        tmf_response = translator.native_to_tmf(resource, data)
        if _should_validate("VALIDATE_RESPONSES"):
            valid, errs = validator.validate(resource, tmf_response.get("data"), direction="native_to_tmf")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Response payload failed validation", 502 if status < 500 else status)
        return jsonify(tmf_response), status

    def put(self, resource: str, item_id: str):
        translator, proxy, validator = _services()
        tmf_payload = request.get_json(silent=True) or {}
        if _should_validate("VALIDATE_REQUESTS"):
            valid, errs = validator.validate(resource, tmf_payload, direction="tmf_to_native")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Request payload failed validation", 400)
        native_payload = translator.tmf_to_native(resource, tmf_payload)
        try:
            data, status = proxy.forward("PUT", f"/{resource}/{item_id}", json=native_payload, headers=_forward_auth_headers())
        except UpstreamUnavailableError as e:
            inc_counter("proxy_errors")
            return _error("UpstreamUnavailable", str(e), 502)
        tmf_response = translator.native_to_tmf(resource, data)
        if _should_validate("VALIDATE_RESPONSES"):
            valid, errs = validator.validate(resource, tmf_response.get("data"), direction="native_to_tmf")
            if not valid:
                inc_counter("validation_failures")
                return _error("ValidationFailed", "Response payload failed validation", 502 if status < 500 else status)
        return jsonify(tmf_response), status

    def delete(self, resource: str, item_id: str):
        translator, proxy, validator = _services()
        try:
            data, status = proxy.forward("DELETE", f"/{resource}/{item_id}", headers=_forward_auth_headers())
        except UpstreamUnavailableError as e:
            inc_counter("proxy_errors")
            return _error("UpstreamUnavailable", str(e), 502)
        tmf_response = translator.native_to_tmf(resource, data)
        return jsonify(tmf_response), status

def _forward_auth_headers():
    # Optionally forward Authorization header from incoming request
    hdrs = {}
    auth = request.headers.get("Authorization")
    if auth:
        hdrs["Authorization"] = auth
    # forward API key header if present
    api_key_header = current_app.config.get("UPSTREAM_API_KEY_HEADER", "X-API-Key")
    if request.headers.get(api_key_header):
        hdrs[api_key_header] = request.headers.get(api_key_header)
    return hdrs

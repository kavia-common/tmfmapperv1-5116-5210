from flask import Flask, request, g
import uuid
import time
import logging

logger = logging.getLogger("observability")

# PUBLIC_INTERFACE
def register_observability_middleware(app: Flask):
    """Register request ID propagation and basic timing for all requests."""

    @app.before_request
    def _inject_request_id():
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # store in environ and flask.g
        request.environ["request_id"] = rid
        g.request_start = time.time()
        # also propagate back in response via after_request
        # structured start log
        logger.info(f"request_start method={request.method} path={request.path} request_id={rid}")

    @app.after_request
    def _add_request_id_header(response):
        rid = request.environ.get("request_id")
        if rid:
            response.headers["X-Request-ID"] = rid
        # timing metric logging
        try:
            dur_ms = int((time.time() - getattr(g, "request_start", time.time())) * 1000)
        except Exception:
            dur_ms = -1
        logger.info(f"request_end method={request.method} path={request.path} status={response.status_code} duration_ms={dur_ms} request_id={rid}")
        return response

from flask import Blueprint, jsonify
from time import time
import threading

_metrics = {
    "total_requests": 0,
    "proxy_errors": 0,
    "validation_failures": 0,
    "latency_ms": {
        "count": 0,
        "total": 0,
        "max": 0,
        "min": None,
    },
}
_lock = threading.RLock()

blp = Blueprint("Metrics", "metrics", url_prefix="/", description="Metrics endpoint")

def _record_latency(ms: int):
    with _lock:
        agg = _metrics["latency_ms"]
        agg["count"] += 1
        agg["total"] += ms
        agg["max"] = max(agg["max"], ms)
        agg["min"] = ms if agg["min"] is None else min(agg["min"], ms)

# PUBLIC_INTERFACE
def inc_counter(name: str, amount: int = 1):
    """Increment a named counter safely."""
    with _lock:
        _metrics[name] = int(_metrics.get(name, 0)) + amount

# PUBLIC_INTERFACE
def record_request_metrics(start_ts: float):
    """Record metrics for a request given its start timestamp."""
    try:
        dur_ms = int((time() - start_ts) * 1000)
    except Exception:
        dur_ms = 0
    with _lock:
        _metrics["total_requests"] = int(_metrics.get("total_requests", 0)) + 1
    _record_latency(dur_ms)

# PUBLIC_INTERFACE
@blp.route("/metrics", methods=["GET"])
def get_metrics():
    """Return current metrics counters and latency aggregates."""
    with _lock:
        counts = {k: v for k, v in _metrics.items() if k in ("total_requests", "proxy_errors", "validation_failures")}
        lat = _metrics.get("latency_ms", {})
        avg = (lat["total"] / lat["count"]) if lat.get("count") else 0
        body = {
            "counters": counts,
            "latency_ms": {
                "count": lat.get("count", 0),
                "avg": int(avg),
                "max": lat.get("max", 0),
                "min": lat.get("min") if lat.get("min") is not None else 0,
            },
        }
    return jsonify(body)

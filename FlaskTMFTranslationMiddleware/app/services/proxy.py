from typing import Any, Dict, Optional, Tuple
import requests
from urllib.parse import urljoin
from app.utils.errors import UpstreamUnavailableError

class ProxyService:
    """
    Forwards requests to the Django inventory application.
    """

    def __init__(self, base_url: str, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/") + "/"
        self.session = session or requests.Session()

    # PUBLIC_INTERFACE
    def forward(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> Tuple[Any, int]:
        """
        Forward a request to the upstream Django app and return JSON payload and status code.

        Raises UpstreamUnavailableError if the upstream is unreachable.
        """
        url = urljoin(self.base_url, path.lstrip("/"))
        try:
            resp = self.session.request(method=method.upper(), url=url, params=params, json=json, timeout=10)
        except requests.RequestException as e:
            raise UpstreamUnavailableError(f"Failed to reach upstream {self.base_url}: {e}") from e

        content_type = resp.headers.get("Content-Type", "")
        try:
            data = resp.json() if "application/json" in content_type.lower() else {"raw": resp.text}
        except ValueError:
            data = {"raw": resp.text}
        return data, resp.status_code

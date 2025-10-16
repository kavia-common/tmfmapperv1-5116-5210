from typing import Any, Dict, Optional, Tuple
import time
import requests
from urllib.parse import urljoin
from app.utils.errors import UpstreamUnavailableError

class ProxyService:
    """
    Forwards requests to the Django inventory application with timeout, retries, and optional auth headers.
    """

    def __init__(
        self,
        base_url: str,
        session: Optional[requests.Session] = None,
        timeout_seconds: float = 10.0,
        retry_count: int = 1,
        static_bearer: str = "",
        api_key: str = "",
        api_key_header: str = "X-API-Key",
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.retry_count = max(0, retry_count)
        self.static_bearer = static_bearer.strip()
        self.api_key = api_key.strip()
        self.api_key_header = api_key_header or "X-API-Key"

    def _build_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.static_bearer:
            headers["Authorization"] = f"Bearer {self.static_bearer}"
        if self.api_key:
            headers[self.api_key_header] = self.api_key
        if extra_headers:
            headers.update(extra_headers)
        return headers

    # PUBLIC_INTERFACE
    def forward(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[Any, int]:
        """
        Forward a request to the upstream Django app and return JSON payload and status code.

        Raises UpstreamUnavailableError if the upstream is unreachable after retries.
        """
        url = urljoin(self.base_url, path.lstrip("/"))
        last_exc: Optional[Exception] = None
        attempts = self.retry_count + 1
        for attempt in range(attempts):
            try:
                resp = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json,
                    headers=self._build_headers(headers),
                    timeout=self.timeout_seconds,
                )
                content_type = resp.headers.get("Content-Type", "")
                try:
                    data = resp.json() if "application/json" in content_type.lower() else {"raw": resp.text}
                except ValueError:
                    data = {"raw": resp.text}
                return data, resp.status_code
            except requests.RequestException as e:
                last_exc = e
                if attempt < attempts - 1:
                    time.sleep(0.2 * (attempt + 1))
                    continue
        raise UpstreamUnavailableError(f"Failed to reach upstream {self.base_url}: {last_exc}")

    # PUBLIC_INTERFACE
    def health(self) -> Tuple[bool, Optional[int]]:
        """
        Perform a simple upstream health check against base URL.
        """
        try:
            resp = self.session.get(self.base_url, timeout=self.timeout_seconds)
            return True, resp.status_code
        except requests.RequestException:
            return False, None

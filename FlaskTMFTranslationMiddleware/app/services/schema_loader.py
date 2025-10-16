import json
import os
import threading
from typing import Any, Dict, Optional
import requests
from datetime import datetime

class SchemaLoader:
    """
    Loads the native OpenAPI schema from a URL or local file with graceful fallback.
    Maintains an in-memory cache and supports dynamic reloads.
    Thread-safe access with conditional HTTP caching (ETag/Last-Modified).
    """

    def __init__(self, url: Optional[str], local_path: str, session: Optional[requests.Session] = None):
        self.url = (url or "").strip()
        self.local_path = (local_path or "").strip()
        self.session = session or requests.Session()
        self.schema: Optional[Dict[str, Any]] = None
        self._source_used: str = "none"
        self._lock = threading.RLock()
        # Conditional caching
        self._etag: Optional[str] = None
        self._last_modified: Optional[str] = None
        self._last_loaded_at: Optional[str] = None

    def _load_from_file(self) -> Optional[Dict[str, Any]]:
        if self.local_path and os.path.exists(self.local_path):
            with open(self.local_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)
                self._source_used = f"file:{self.local_path}"
                self._last_loaded_at = datetime.utcnow().isoformat() + "Z"
                # file cannot provide etag/last-modified; reset
                self._etag = None
                self._last_modified = None
                return self.schema
        return None

    def _load_from_url(self) -> Optional[Dict[str, Any]]:
        if not self.url:
            return None
        headers = {}
        if self._etag:
            headers["If-None-Match"] = self._etag
        if self._last_modified:
            headers["If-Modified-Since"] = self._last_modified
        try:
            resp = self.session.get(self.url, timeout=10, headers=headers)
            if resp.status_code == 304 and self.schema is not None:
                # Not modified; keep current schema
                self._source_used = f"url:{self.url} (304 not modified)"
                return self.schema
            resp.raise_for_status()
            self.schema = resp.json()
            self._source_used = f"url:{self.url}"
            self._etag = resp.headers.get("ETag") or self._etag
            self._last_modified = resp.headers.get("Last-Modified") or self._last_modified
            self._last_loaded_at = datetime.utcnow().isoformat() + "Z"
            return self.schema
        except Exception:
            return None

    # PUBLIC_INTERFACE
    def load_schema(self) -> Dict[str, Any]:
        """Loads the schema prioritizing explicit local path if provided, otherwise URL, then fallback to bundled path."""
        with self._lock:
            # 1) Prefer explicit local file if provided and no URL, or exists
            schema = None
            if self.local_path and (os.path.isabs(self.local_path) or os.path.exists(self.local_path)) and not self.url:
                schema = self._load_from_file()

            # 2) Try URL next
            if schema is None:
                schema = self._load_from_url()

            # 3) If still none, try local (bundled or provided path)
            if schema is None:
                schema = self._load_from_file()

            # 4) Fallback to empty
            if schema is None:
                self.schema = {"openapi": "3.0.0", "paths": {}, "components": {}}
                self._source_used = "empty"
                self._last_loaded_at = datetime.utcnow().isoformat() + "Z"
                return self.schema

            return schema

    # PUBLIC_INTERFACE
    def get_schema(self) -> Dict[str, Any]:
        """Returns the current schema, loading it on demand if missing."""
        with self._lock:
            if self.schema is None:
                return self.load_schema()
            return self.schema

    # PUBLIC_INTERFACE
    def reload(self) -> Dict[str, Any]:
        """Force reload of the schema. Uses conditional headers when URL is configured."""
        with self._lock:
            # Reset file timestamp markers; keep etag/last-modified for conditional GET
            return self.load_schema()

    # PUBLIC_INTERFACE
    def source_info(self) -> str:
        """Return a short description of where the schema was loaded from, including metadata."""
        with self._lock:
            meta = {
                "source": self._source_used,
                "etag": self._etag,
                "lastModified": self._last_modified,
                "lastLoadedAt": self._last_loaded_at,
            }
            return json.dumps(meta)

import json
import os
from typing import Any, Dict, Optional
import requests

class SchemaLoader:
    """
    Loads the native OpenAPI schema from a URL or local file with graceful fallback.
    Maintains an in-memory cache and supports future dynamic reloads.
    """

    def __init__(self, url: Optional[str], local_path: str, session: Optional[requests.Session] = None):
        self.url = (url or "").strip()
        self.local_path = (local_path or "").strip()
        self.session = session or requests.Session()
        self.schema: Optional[Dict[str, Any]] = None
        self._source_used: str = "none"

    # PUBLIC_INTERFACE
    def load_schema(self) -> Dict[str, Any]:
        """Loads the schema prioritizing explicit local path if provided, otherwise URL, then fallback to bundled path."""
        # 1) If an explicit local path was provided (NATIVE_OPENAPI_PATH), try it first
        if self.local_path and os.path.isabs(self.local_path) or (self.local_path and os.path.exists(self.local_path) and not self.url):
            try:
                if os.path.exists(self.local_path):
                    with open(self.local_path, "r", encoding="utf-8") as f:
                        self.schema = json.load(f)
                        self._source_used = f"file:{self.local_path}"
                        return self.schema
            except Exception:
                # Continue to URL fallback
                pass

        # 2) Try URL if present
        if self.url:
            try:
                resp = self.session.get(self.url, timeout=10)
                resp.raise_for_status()
                self.schema = resp.json()
                self._source_used = f"url:{self.url}"
                return self.schema
            except Exception:
                # Fall back to local (bundled or provided path)
                pass

        # 3) Fallback to local file if exists (bundled path or provided path)
        if self.local_path and os.path.exists(self.local_path):
            with open(self.local_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)
                self._source_used = f"file:{self.local_path}"
                return self.schema

        # If all fails, set empty schema structure
        self.schema = {"openapi": "3.0.0", "paths": {}, "components": {}}
        self._source_used = "empty"
        return self.schema

    # PUBLIC_INTERFACE
    def get_schema(self) -> Dict[str, Any]:
        """Returns the current schema, loading it on demand if missing."""
        if self.schema is None:
            return self.load_schema()
        return self.schema

    # PUBLIC_INTERFACE
    def reload(self) -> Dict[str, Any]:
        """Force reload of the schema (placeholder for dynamic schema evolution hooks)."""
        return self.load_schema()

    # PUBLIC_INTERFACE
    def source_info(self) -> str:
        """Return a short description of where the schema was loaded from."""
        return self._source_used

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
        self.local_path = local_path
        self.session = session or requests.Session()
        self.schema: Optional[Dict[str, Any]] = None

    # PUBLIC_INTERFACE
    def load_schema(self) -> Dict[str, Any]:
        """Loads the schema from URL if provided else falls back to local file."""
        # Try URL first if present
        if self.url:
            try:
                resp = self.session.get(self.url, timeout=10)
                resp.raise_for_status()
                self.schema = resp.json()
                return self.schema
            except Exception:
                # Fall back to local
                pass

        # Fallback to local file if exists
        if os.path.exists(self.local_path):
            with open(self.local_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)
                return self.schema

        # If all fails, set empty schema structure
        self.schema = {"openapi": "3.0.0", "paths": {}, "components": {}}
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

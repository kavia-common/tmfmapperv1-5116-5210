from typing import Dict, Any, Callable, Union
from copy import deepcopy

MappingFunc = Callable[[Dict[str, Any]], Dict[str, Any]]

def _rename_fields(data: Dict[str, Any], mapping: Dict[str, str], passthrough: bool = True) -> Dict[str, Any]:
    """Utility: rename keys according to mapping; optionally pass through unknown keys unchanged."""
    out: Dict[str, Any] = {}
    for k, v in (data or {}).items():
        new_k = mapping.get(k, k) if passthrough else mapping.get(k)
        if new_k is None:
            continue
        out[new_k] = v
    return out

def _normalize_id(value: Any) -> Any:
    """Normalize id types to string for TMF compatibility."""
    if value is None:
        return value
    return str(value)

class TranslatorService:
    """
    Translates between TMF-formatted requests/responses and the native Django app format.

    A simple registry maps resource names to direction-specific field rename maps and optional custom hooks.
    Unmapped fields are passed through by default.
    """

    def __init__(self, schema_loader):
        self.schema_loader = schema_loader
        # Simple example registry with "Item" mapping
        # tmf_to_native: TMF -> Native names; native_to_tmf: Native -> TMF names
        self.registry: Dict[str, Dict[str, Union[Dict[str, str], MappingFunc]]] = {
            "Item": {
                "tmf_to_native": {
                    "id": "id",
                    "name": "name",
                    "quantity": "quantity",
                },
                "native_to_tmf": {
                    "id": "id",
                    "name": "name",
                    "quantity": "quantity",
                },
                # optional post processors
                "tmf_post": self._item_tmf_post,
                "native_post": self._item_native_post,
                # query mapping example (TMF query param -> native)
                "query": {
                    "id": "id",
                    "name": "name",
                },
            }
        }

    def _get_entry(self, resource: str) -> Dict[str, Any]:
        # Case-insensitive lookup
        for key, entry in self.registry.items():
            if key.lower() == (resource or "").lower():
                return entry
        return {}

    def _apply_query_mapping(self, resource: str, params: Dict[str, Any]) -> Dict[str, Any]:
        entry = self._get_entry(resource)
        qmap = entry.get("query", {}) if entry else {}
        return _rename_fields(params or {}, qmap, passthrough=True)

    def _item_tmf_post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Example: ensure id normalized to native expectations (string ok)
        if "id" in data:
            data["id"] = _normalize_id(data["id"])
        return data

    def _item_native_post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Example: ensure id is string in TMF
        if isinstance(data, dict) and "id" in data:
            data["id"] = _normalize_id(data["id"])
        return data

    # PUBLIC_INTERFACE
    def tmf_to_native(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a TMF request payload (or query params) into the native format.
        Applies a resource-specific field mapping; unknown fields are passed through.
        """
        entry = self._get_entry(resource)
        mapping: Dict[str, str] = entry.get("tmf_to_native", {}) if entry else {}
        mapped = _rename_fields(payload or {}, mapping, passthrough=True)
        post: MappingFunc = entry.get("tmf_post") if entry else None
        return post(mapped) if callable(post) else mapped

    # PUBLIC_INTERFACE
    def translate_query_params(self, resource: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Translate TMF query params to native ones using registry; pass-through otherwise."""
        return self._apply_query_mapping(resource, params or {})

    # PUBLIC_INTERFACE
    def native_to_tmf(self, resource: str, payload: Any) -> Dict[str, Any]:
        """
        Translate a native response payload into TMF format.
        Performs field renames on dicts and lists of dicts; other payloads are wrapped.
        """
        entry = self._get_entry(resource)
        mapping: Dict[str, str] = entry.get("native_to_tmf", {}) if entry else {}

        def map_one(obj: Dict[str, Any]) -> Dict[str, Any]:
            out = _rename_fields(obj, mapping, passthrough=True)
            return entry.get("native_post")(out) if entry and callable(entry.get("native_post")) else out

        if isinstance(payload, list):
            return {"data": [map_one(x) if isinstance(x, dict) else x for x in payload]}
        if isinstance(payload, dict):
            return {"data": map_one(deepcopy(payload))}
        return {"data": {"value": payload}}

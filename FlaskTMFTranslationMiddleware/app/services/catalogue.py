from typing import Any, Dict, List
import datetime

class CatalogueService:
    """
    Generates a simplified TMF-like resource catalogue derived from the native schema.
    """

    def __init__(self, schema_loader):
        self.schema_loader = schema_loader

    # PUBLIC_INTERFACE
    def generate_catalogue(self) -> List[Dict[str, Any]]:
        """
        Produces a catalogue list: [{resource, description, fields: [{name, type}]}]
        """
        schema = self.schema_loader.get_schema()
        components = (schema or {}).get("components", {}).get("schemas", {}) or {}
        items = []
        for name, spec in components.items():
            if spec.get("type") == "object":
                fields = []
                for prop_name, prop_spec in (spec.get("properties") or {}).items():
                    ftype = prop_spec.get("type") or prop_spec.get("$ref", "object")
                    fields.append({"name": prop_name, "type": ftype})
                items.append({
                    "resource": name,
                    "description": spec.get("description", ""),
                    "fields": fields
                })
        return items

    def schema_info(self) -> Dict[str, Any]:
        """Basic info to expose along with the catalogue."""
        schema = self.schema_loader.get_schema()
        return {
            "openapi": schema.get("openapi"),
            "generatedAt": datetime.datetime.utcnow().isoformat() + "Z"
        }

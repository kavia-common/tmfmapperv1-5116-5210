from typing import Any, Dict, List
import datetime

class CatalogueService:
    """
    Generates a simplified TMF-like resource catalogue derived from the native schema.
    """

    def __init__(self, schema_loader):
        self.schema_loader = schema_loader

    def _crud_from_paths(self, resource_name: str, paths: Dict[str, Any]) -> Dict[str, bool]:
        """Infer CRUD capabilities from OpenAPI paths by common REST naming."""
        res = resource_name
        plural = f"/{res.lower()}s"
        singular = f"/{res.lower()}"
        caps = {"canCreate": False, "canRead": False, "canUpdate": False, "canDelete": False}
        for p, path_item in (paths or {}).items():
            # naive matching on endpoints that contain resource name
            if res.lower() in p.lower():
                methods = {m.lower() for m in path_item.keys()}
                if "get" in methods:
                    caps["canRead"] = True
                if "post" in methods:
                    caps["canCreate"] = True
                if "put" in methods or "patch" in methods:
                    caps["canUpdate"] = True
                if "delete" in methods:
                    caps["canDelete"] = True
            # some naive pluralization checks
            if p.lower().startswith(plural):
                methods = {m.lower() for m in path_item.keys()}
                if "get" in methods:
                    caps["canRead"] = True
                if "post" in methods:
                    caps["canCreate"] = True
            if p.lower().startswith(singular + "/") or p.lower().startswith(plural + "/"):
                methods = {m.lower() for m in path_item.keys()}
                if "get" in methods:
                    caps["canRead"] = True
                if "put" in methods or "patch" in methods:
                    caps["canUpdate"] = True
                if "delete" in methods:
                    caps["canDelete"] = True
        return caps

    # PUBLIC_INTERFACE
    def generate_catalogue(self) -> List[Dict[str, Any]]:
        """
        Produces a catalogue list with TMF-like shape:
        [{resource, description, keyAttributes, attributes: [{name, type, required}], capabilities:{canCreate,canRead,canUpdate,canDelete}}]
        """
        schema = self.schema_loader.get_schema()
        components = (schema or {}).get("components", {}).get("schemas", {}) or {}
        paths = (schema or {}).get("paths", {}) or {}
        items = []
        for name, spec in components.items():
            if spec.get("type") == "object":
                properties = spec.get("properties") or {}
                required = set(spec.get("required") or [])
                attributes = []
                key_attrs = []
                for prop_name, prop_spec in properties.items():
                    ftype = prop_spec.get("type") or prop_spec.get("$ref", "object")
                    attributes.append({
                        "name": prop_name,
                        "type": ftype,
                        "required": prop_name in required
                    })
                    # consider 'id' or explicitly required fields as key attributes
                    if prop_name.lower() == "id" or prop_name in required:
                        key_attrs.append(prop_name)
                capabilities = self._crud_from_paths(name, paths)
                items.append({
                    "resource": name,
                    "description": spec.get("description", ""),
                    "keyAttributes": sorted(list(set(key_attrs))),
                    "attributes": attributes,
                    "capabilities": capabilities
                })
        return items

    def schema_info(self) -> Dict[str, Any]:
        """Basic info to expose along with the catalogue."""
        schema = self.schema_loader.get_schema()
        return {
            "openapi": schema.get("openapi"),
            "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
            "source": getattr(self.schema_loader, "source_info", lambda: "unknown")()
        }

from typing import Any, Dict, Tuple
from jsonschema import Draft7Validator, RefResolver, exceptions as jsonschema_exceptions

class ValidationService:
    """
    Performs basic runtime validation of payloads against the loaded native OpenAPI schema.
    Direction-aware hooks are provided for tmf_to_native (request) vs native_to_tmf (response).
    """

    def __init__(self, schema_loader):
        self.schema_loader = schema_loader

    def _find_schema_for_resource(self, resource: str) -> Dict[str, Any]:
        """
        Basic attempt to derive a schema for a resource from OpenAPI.
        Strategy:
          - look for components/schemas with a title/name matching resource (case-insensitive)
          - fallback to any object schema
        """
        schema = self.schema_loader.get_schema()
        components = (schema or {}).get("components", {}).get("schemas", {}) or {}
        # Case-insensitive match on key or title
        for name, spec in components.items():
            title = spec.get("title") or name
            if str(name).lower() == (resource or "").lower() or str(title).lower() == (resource or "").lower():
                return spec
        # Fallback to any object-like schema
        for spec in components.values():
            if spec.get("type") == "object":
                return spec
        # Default to permissive any
        return {"type": "object"}

    def _directional_adjustments(self, direction: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply minor adjustments depending on direction.
        Example: for responses (native_to_tmf), do not require write-only fields, etc.
        For now, return schema unchanged.
        """
        return schema

    # PUBLIC_INTERFACE
    def validate(self, resource: str, payload: Any, direction: str = "tmf_to_native") -> Tuple[bool, list]:
        """Validate a payload for the given resource and direction against the derived schema."""
        try:
            base_schema = self._find_schema_for_resource(resource or "")
            effective_schema = self._directional_adjustments(direction, base_schema)
            resolver = RefResolver.from_schema(self.schema_loader.get_schema())
            validator = Draft7Validator(effective_schema, resolver=resolver)
            errors = sorted(validator.iter_errors(payload or {}), key=lambda e: e.path)
            if errors:
                return False, [f"{'/'.join([str(p) for p in e.path])}: {e.message}" for e in errors]
            return True, []
        except jsonschema_exceptions.SchemaError as e:
            return False, [f"Invalid schema for resource {resource}: {e.message}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

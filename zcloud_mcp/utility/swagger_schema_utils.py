"""
Generic swagger/OpenAPI schema parsing utilities.

This module provides reusable functions for parsing swagger/OpenAPI specifications
and extracting schema structures. It can be used by any service that needs to
introspect API schemas.

Service-specific swagger configuration (endpoint mappings, caching, initialization)
lives in the respective service's utility module (e.g., mcp/utility/swagger_config.py).
"""

from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_schema_structure(
    swagger_spec: dict,
    schema_name: str,
    visited: Optional[set] = None
) -> dict[str, Any]:
    """
    Extract complete field structure from a swagger schema, resolving all $refs.

    Returns a clean structure showing all fields with their types and descriptions,
    including nested object/array fields fully expanded. Circular references are
    detected via the visited set and shown as a reference note instead of recursing
    infinitely.

    Args:
        swagger_spec: The full swagger/OpenAPI specification dictionary
        schema_name: Name of the schema definition to extract
        visited: Set of already-visited schema names to prevent infinite recursion (internal use)

    Returns:
        Dictionary mapping field names to their type information and descriptions
    """
    if visited is None:
        visited = set()

    if schema_name in visited:
        return {"_type": "object", "_schema": schema_name, "_note": "circular reference, see above"}

    visited.add(schema_name)
    definitions = swagger_spec.get("definitions", {})
    schema = definitions.get(schema_name)

    if not schema:
        return {"_error": f"Schema '{schema_name}' not found"}

    result = {}
    properties = schema.get("properties", {})

    for field_name, field_def in properties.items():
        field_type = field_def.get("type", "object")
        description = field_def.get("description", "")

        # Handle $ref - resolve to nested type
        if "$ref" in field_def:
            ref_schema = field_def["$ref"].replace("#/definitions/", "")
            nested = get_schema_structure(
                swagger_spec, ref_schema, visited.copy()
            )
            result[field_name] = {
                "_type": "object",
                "_description": description,
                "_fields": nested
            }
        # Handle array with $ref items
        elif field_type == "array" and "$ref" in field_def.get("items", {}):
            ref_schema = field_def["items"]["$ref"].replace("#/definitions/", "")
            nested = get_schema_structure(
                swagger_spec, ref_schema, visited.copy()
            )
            result[field_name] = {
                "_type": "array",
                "_description": description,
                "_item_fields": nested
            }
        # Handle simple array
        elif field_type == "array":
            item_type = field_def.get("items", {}).get("type", "string")
            result[field_name] = {
                "_type": f"array<{item_type}>",
                "_description": description
            }
        # Handle simple types
        else:
            result[field_name] = {
                "_type": field_type,
                "_description": description
            }

    return result

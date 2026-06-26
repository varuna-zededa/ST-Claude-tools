"""
Generic JSON parsing and field extraction utilities.

This module provides reusable functions for efficiently extracting specific fields
from JSON responses using JMESPath expressions. It can be used by any service
that needs structured JSON field filtering.

Design Principles:
- Use JMESPath for declarative, efficient field extraction
- Support both basic (always included) and additional (on-demand) fields
- Provide helpful metadata about the filtering for debugging
- Handle edge cases gracefully with fallbacks

Usage:
    from utility.json_utils import JsonFieldExtractor

    # Define your field configuration
    extractor = JsonFieldExtractor(
        basic_fields=["id", "name", "status"],
        additional_fields=["details", "metadata", "config"],
        list_key="list"  # The key containing the list of items
    )

    # Extract fields from response
    filtered = extractor.filter_response(api_response, {"details": True, "config": True})
"""

from typing import Any, Optional
import jmespath
import logging

logger = logging.getLogger(__name__)


class JsonFieldExtractor:
    """
    A reusable class for extracting specific fields from JSON responses using JMESPath.

    This class provides a declarative way to define which fields should always be included
    (basic fields) and which fields can be optionally requested (additional fields).

    Attributes:
        basic_fields: List of field names that are always included in the response
        additional_fields: List of field names that can be optionally requested
        list_key: The key in the response that contains the list of items to filter
        summary_keys: List of keys for summary/metadata that should always be preserved
    """

    def __init__(
        self,
        basic_fields: list[str],
        additional_fields: Optional[list[str]] = None,
        list_key: str = "list",
        summary_keys: Optional[list[str]] = None,
    ):
        """
        Initialize the JsonFieldExtractor.

        Args:
            basic_fields: Fields that are always included in the filtered response
            additional_fields: Fields that can be optionally requested (empty list means LLM discovers dynamically)
            list_key: The key containing the list of items (default: "list")
            summary_keys: Keys for summary data to preserve (empty list means LLM discovers dynamically)
        """
        self.basic_fields = basic_fields
        self.additional_fields = additional_fields or []
        self.list_key = list_key
        self.summary_keys = summary_keys or []

    def build_jmespath_expression(
        self,
        requested_fields: Optional[dict[str, bool]] = None
    ) -> str:
        """
        Build a JMESPath expression to extract specified fields from each item.

        Args:
            requested_fields: Dictionary of field names to include (key: field name, value: True to include)

        Returns:
            JMESPath expression string for extracting the specified fields

        Example:
            >>> extractor = JsonFieldExtractor(["id", "name"], ["status", "config"])
            >>> extractor.build_jmespath_expression({"status": True})
            'list[*].{id: id, name: name, status: status}'
        """
        # Start with basic fields
        fields_to_extract = self.basic_fields.copy()

        # Add requested additional fields - accept ANY field name discovered by caller
        if requested_fields:
            for field, include in requested_fields.items():
                if include and field not in fields_to_extract:
                    fields_to_extract.append(field)

        # Build JMESPath projection expression: {id: id, name: name, ...}
        field_projections = ", ".join([f"{f}: {f}" for f in fields_to_extract])
        return f"{self.list_key}[*].{{{field_projections}}}"

    def extract_fields_from_list(
        self,
        data: dict,
        requested_fields: Optional[dict[str, bool]] = None,
    ) -> list[dict]:
        """
        Extract specified fields from a list of items using JMESPath.

        Args:
            data: The full response dictionary containing the list
            requested_fields: Dictionary of additional fields to include

        Returns:
            List of dictionaries with only the requested fields
        """
        if self.list_key not in data or not data[self.list_key]:
            return []

        try:
            jmespath_expr = self.build_jmespath_expression(requested_fields)
            result = jmespath.search(jmespath_expr, data)
            return result if result else []
        except Exception as e:
            logger.warning(f"JMESPath extraction failed: {e}, returning empty list")
            return []

    def extract_field(self, data: dict, field_path: str) -> Any:
        """
        Extract a single field or nested field using JMESPath.

        Args:
            data: The dictionary to extract from
            field_path: JMESPath expression for the field (e.g., "user.name" or "items[0].id")

        Returns:
            The extracted value, or None if not found
        """
        try:
            return jmespath.search(field_path, data)
        except Exception as e:
            logger.warning(f"JMESPath field extraction failed for '{field_path}': {e}")
            return None

    def extract_multiple_fields(self, data: dict, field_paths: list[str]) -> dict[str, Any]:
        """
        Extract multiple fields using JMESPath expressions.

        Args:
            data: The dictionary to extract from
            field_paths: List of JMESPath expressions

        Returns:
            Dictionary mapping field paths to their extracted values
        """
        result = {}
        for path in field_paths:
            result[path] = self.extract_field(data, path)
        return result

    def filter_response(
        self,
        response: dict,
        requested_fields: Optional[dict[str, bool]] = None,
        include_metadata: bool = False,
        include_summaries: bool = True,
        exclude_summary_keys: Optional[list[str]] = None,
        return_complete: bool = False,
    ) -> dict:
        """
        Filter a full API response to include only the requested fields.

        This method:
        1. Extracts only the specified fields from items in the list
        2. Optionally preserves summary and pagination information
        3. Optionally adds metadata about the filtering (disabled by default to save tokens)
        4. Can return complete unfiltered response when return_complete=True

        Args:
            response: The full API response dictionary
            requested_fields: Dictionary of additional fields to include
            include_metadata: Whether to include _field_info metadata (default: False to save tokens)
            include_summaries: Whether to include summary data (default: True)
            exclude_summary_keys: List of specific summary keys to exclude (e.g., ["summaryByEVEDistribution"])
            return_complete: If True, return complete unfiltered response (default: False)

        Returns:
            Filtered response dictionary with only the requested fields,
            or complete response if return_complete=True
        """
        # Return complete mode: return full API response as-is
        if return_complete:
            logger.debug("Returning complete unfiltered response")
            return response

        filtered_response = {}

        # Extract only the needed fields from the list using JMESPath
        if self.list_key in response and response[self.list_key]:
            try:
                jmespath_expr = self.build_jmespath_expression(requested_fields)
                filtered_list = jmespath.search(jmespath_expr, response)
                filtered_response[self.list_key] = filtered_list if filtered_list else []
            except Exception as e:
                logger.warning(f"JMESPath extraction failed: {e}, falling back to original list")
                filtered_response[self.list_key] = response.get(self.list_key, [])
        else:
            filtered_response[self.list_key] = []

        # Preserve summary and pagination info using JMESPath
        if include_summaries:
            excluded = set(exclude_summary_keys or [])
            for key in self.summary_keys:
                if key in excluded:
                    continue
                value = jmespath.search(key, response)
                if value is not None:
                    filtered_response[key] = value

        # Always preserve pagination and count info
        pagination_keys = ["next", "totalCount", "total"]
        for key in pagination_keys:
            if key in response:
                filtered_response[key] = response[key]

        # Add pagination warning when the response contains only a subset of total records.
        # This prevents LLM agents from making sweeping conclusions (e.g., "no devices have
        # location set") based on a single page of results.
        next_info = response.get("next", {})
        total_pages = next_info.get("totalPages", 1) if isinstance(next_info, dict) else 1
        current_page = next_info.get("pageNum", 1) if isinstance(next_info, dict) else 1
        page_size = next_info.get("pageSize", 0) if isinstance(next_info, dict) else 0
        total_count = response.get("totalCount", 0) or 0
        items_on_page = len(response.get(self.list_key, []))

        if total_pages > 1:
            filtered_response["_pagination_notice"] = (
                f"This response contains page {current_page} of {total_pages} "
                f"({items_on_page} of {total_count} total records). "
                f"LISTING queries (e.g. 'show me my devices', 'list projects'): "
                f"Present these results and ask the user if they want the next page. "
                f"Do NOT automatically paginate. "
                f"ANALYTICAL queries (e.g. 'which devices have X', 'how many nodes are online', "
                f"'do any devices have errors'): "
                f"You MUST paginate through ALL {total_pages} pages before drawing conclusions. "
                f"Never state 'none found' or 'all have X' based on partial data."
            )

        # Add metadata about the filtering
        if include_metadata:
            requested_field_names = [
                f for f, include in (requested_fields or {}).items() if include
            ]
            filtered_response["_field_info"] = {
                "basic_fields_included": self.basic_fields,
                "additional_fields_requested": requested_field_names,
                "available_additional_fields": self.additional_fields,
                "jmespath_expression": (
                    self.build_jmespath_expression(requested_fields)
                    if response.get(self.list_key)
                    else None
                ),
            }

        return filtered_response


def extract_nested_field(data: dict, path: str, default: Any = None) -> Any:
    """
    Extract a nested field from a dictionary using JMESPath.

    This is a convenience function for one-off field extractions.

    Args:
        data: The dictionary to extract from
        path: JMESPath expression (e.g., "user.profile.name", "items[0].id", "data[*].name")
        default: Default value if field is not found

    Returns:
        The extracted value, or default if not found

    Examples:
        >>> data = {"user": {"name": "John", "age": 30}}
        >>> extract_nested_field(data, "user.name")
        'John'
        >>> extract_nested_field(data, "user.email", "N/A")
        'N/A'
    """
    try:
        result = jmespath.search(path, data)
        return result if result is not None else default
    except Exception as e:
        logger.warning(f"JMESPath extraction failed for path '{path}': {e}")
        return default


def filter_list_fields(
    items: list[dict],
    fields: list[str],
) -> list[dict]:
    """
    Filter a list of dictionaries to include only specified fields.

    Args:
        items: List of dictionaries to filter
        fields: List of field names to include

    Returns:
        List of dictionaries with only the specified fields

    Example:
        >>> items = [{"id": 1, "name": "a", "secret": "x"}, {"id": 2, "name": "b", "secret": "y"}]
        >>> filter_list_fields(items, ["id", "name"])
        [{'id': 1, 'name': 'a'}, {'id': 2, 'name': 'b'}]
    """
    if not items or not fields:
        return items

    # Build JMESPath expression for field projection
    field_projections = ", ".join([f"{f}: {f}" for f in fields])
    jmespath_expr = f"[*].{{{field_projections}}}"

    try:
        result = jmespath.search(jmespath_expr, items)
        return result if result else []
    except Exception as e:
        logger.warning(f"JMESPath list filtering failed: {e}")
        return items


def search_json(data: Any, expression: str) -> Any:
    """
    Execute a JMESPath expression on JSON data.

    This is a thin wrapper around jmespath.search with error handling.

    Args:
        data: JSON data (dict, list, etc.)
        expression: JMESPath expression

    Returns:
        Result of the JMESPath query, or None on error

    Examples:
        >>> data = {"items": [{"name": "a"}, {"name": "b"}]}
        >>> search_json(data, "items[*].name")
        ['a', 'b']
        >>> search_json(data, "items[?name=='a']")
        [{'name': 'a'}]
    """
    try:
        return jmespath.search(expression, data)
    except Exception as e:
        logger.warning(f"JMESPath search failed for expression '{expression}': {e}")
        return None


def compile_jmespath(expression: str) -> Optional[jmespath.parser.ParsedResult]:
    """
    Compile a JMESPath expression for repeated use.

    Compiled expressions are faster when applied to multiple documents.

    Args:
        expression: JMESPath expression to compile

    Returns:
        Compiled JMESPath expression, or None on error

    Example:
        >>> expr = compile_jmespath("items[*].name")
        >>> if expr:
        ...     result = expr.search({"items": [{"name": "a"}]})
    """
    try:
        return jmespath.compile(expression)
    except Exception as e:
        logger.warning(f"Failed to compile JMESPath expression '{expression}': {e}")
        return None


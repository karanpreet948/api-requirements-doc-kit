"""
apidoc.parser
=============

Reads an OpenAPI 3.0 YAML specification and extracts the pieces of
information a Business Analyst needs in order to write an API
integration requirements document: endpoints, HTTP methods, parameters,
request/response body fields, and documented error responses.

This module deliberately does NOT depend on a full OpenAPI object model
library. The subset of OpenAPI 3.0 handled here is:

* ``paths`` -> path templates -> HTTP methods (get/post/put/patch/delete)
* ``parameters`` (path, query, header) on an operation
* ``requestBody.content.application/json.schema``
* ``responses.<code>.content.application/json.schema``
* local ``$ref`` references into ``components.schemas``

That subset covers the overwhelming majority of "internal system to
internal system" REST APIs a Business Analyst is likely to encounter,
and keeps the parsing logic simple enough to read, test, and trust.

If the specification is missing required top-level sections, or a
referenced schema cannot be resolved, :class:`ApiSpecError` is raised
with a message that is safe to show directly to a non-technical user
(a Business Analyst), rather than letting a raw ``KeyError`` or
``yaml.YAMLError`` propagate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# HTTP methods that OpenAPI allows as keys under a path item.
_HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


class ApiSpecError(Exception):
    """Raised when an OpenAPI specification cannot be read or parsed.

    The message is written to be understandable by a Business Analyst
    reviewing the spec, not just a developer -- e.g. "The specification
    has no 'paths' section" rather than a bare KeyError.
    """


@dataclass
class FieldSpec:
    """A single field in a request/response body, or a single parameter.

    Attributes:
        name: The field or parameter name, exactly as it appears in the spec.
        type: The OpenAPI/JSON Schema type (e.g. ``string``, ``boolean``).
        required: Whether the field is required.
        description: The free-text description from the spec, if any.
        location: Where the field comes from -- ``"path"``, ``"query"``,
            ``"header"``, ``"requestBody"``, or ``"responseBody"``.
        enum_values: Allowed values, if the schema declares an enum.
        format: The OpenAPI ``format`` keyword (e.g. ``uuid``, ``date-time``),
            if present.
    """

    name: str
    type: str
    required: bool
    description: Optional[str]
    location: str
    enum_values: Optional[List[str]] = None
    format: Optional[str] = None

    @property
    def has_business_context(self) -> bool:
        """Whether the spec's description is rich enough to stand on its own.

        A short or missing description is treated as not providing enough
        business context, which the generator uses to decide whether to
        insert a "[BA TO COMPLETE ...]" placeholder.
        """
        return bool(self.description and len(self.description.strip()) >= 12)


@dataclass
class ResponseSpec:
    """A single documented HTTP response for an operation."""

    status_code: str
    description: str
    fields: List[FieldSpec] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.status_code.isdigit() and self.status_code.startswith("2")


@dataclass
class OperationSpec:
    """A single HTTP operation (one method on one path)."""

    path: str
    method: str
    operation_id: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    parameters: List[FieldSpec] = field(default_factory=list)
    request_fields: List[FieldSpec] = field(default_factory=list)
    request_required: bool = False
    responses: List[ResponseSpec] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.method.upper()} {self.path}"

    @property
    def success_response(self) -> Optional[ResponseSpec]:
        for response in self.responses:
            if response.is_success:
                return response
        return None

    @property
    def error_responses(self) -> List[ResponseSpec]:
        return [response for response in self.responses if not response.is_success]


@dataclass
class ApiInfo:
    """The top-level ``info`` block of the specification."""

    title: str
    version: str
    description: Optional[str] = None


@dataclass
class ParsedApiSpec:
    """The fully parsed representation of an OpenAPI specification."""

    info: ApiInfo
    operations: List[OperationSpec] = field(default_factory=list)
    source_path: Optional[str] = None


def _load_yaml(spec_path: Path) -> Dict[str, Any]:
    """Reads and YAML-parses the specification file.

    Raises:
        ApiSpecError: If the file cannot be found or does not contain
            valid YAML, or if the top-level document is not a mapping.
    """
    if not spec_path.exists():
        raise ApiSpecError(f"OpenAPI spec file not found: {spec_path}")

    try:
        raw_text = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ApiSpecError(f"Could not read OpenAPI spec file '{spec_path}': {exc}") from exc

    try:
        document = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ApiSpecError(
            f"'{spec_path}' is not valid YAML and could not be parsed: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise ApiSpecError(
            f"'{spec_path}' does not contain a valid OpenAPI document "
            "(the top level of the file must be a mapping of keys such as "
            "'openapi', 'info', and 'paths')."
        )

    return document


def _resolve_schema(schema: Optional[Dict[str, Any]], components: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves a single local ``$ref`` at the top level of a schema.

    Only local references of the form ``#/components/schemas/<Name>`` are
    supported, which covers every reference used by this tool's example
    spec and the vast majority of hand-authored internal API specs.

    Args:
        schema: The schema mapping to resolve (may itself contain a ``$ref``).
        components: The full ``components`` section of the document, used
            to look up referenced schemas.

    Returns:
        The resolved schema mapping. An empty dict if ``schema`` is falsy.

    Raises:
        ApiSpecError: If a ``$ref`` cannot be resolved.
    """
    if not schema:
        return {}

    if "$ref" in schema:
        ref = schema["$ref"]
        prefix = "#/components/schemas/"
        if not ref.startswith(prefix):
            raise ApiSpecError(
                f"Unsupported $ref '{ref}'. Only local references of the form "
                f"'{prefix}<SchemaName>' are supported by this tool."
            )
        schema_name = ref[len(prefix):]
        schemas = (components or {}).get("schemas", {})
        resolved = schemas.get(schema_name)
        if resolved is None:
            raise ApiSpecError(
                f"The spec references schema '{schema_name}' via '{ref}', "
                "but no such schema is defined under components.schemas."
            )
        return resolved

    return schema


def _fields_from_schema(
    schema: Optional[Dict[str, Any]],
    components: Dict[str, Any],
    location: str,
) -> List[FieldSpec]:
    """Flattens the top-level properties of an object schema into FieldSpecs.

    Nested object properties are represented as a single field of type
    ``object`` (or ``array``) rather than being recursively flattened,
    which keeps the generated data-mapping tables readable -- exactly the
    level of detail a BA typically documents in a requirements doc.
    """
    resolved = _resolve_schema(schema, components)
    if not resolved:
        return []

    schema_type = resolved.get("type", "object")
    if schema_type != "object" and "properties" not in resolved:
        # A schema that is a bare scalar or array at the top level (rare
        # for request/response bodies, but handled gracefully).
        return [
            FieldSpec(
                name="(entire body)",
                type=schema_type or "unknown",
                required=True,
                description=resolved.get("description"),
                location=location,
            )
        ]

    properties: Dict[str, Any] = resolved.get("properties", {}) or {}
    required_names = set(resolved.get("required", []) or [])

    fields: List[FieldSpec] = []
    for prop_name, prop_schema in properties.items():
        prop_resolved = _resolve_schema(prop_schema, components) if isinstance(prop_schema, dict) and "$ref" in prop_schema else (prop_schema or {})
        prop_type = prop_resolved.get("type", "object")
        if prop_type == "array":
            items = prop_resolved.get("items", {}) or {}
            item_resolved = _resolve_schema(items, components) if "$ref" in items else items
            item_type = item_resolved.get("type", "object")
            prop_type = f"array[{item_type}]"

        fields.append(
            FieldSpec(
                name=prop_name,
                type=prop_type,
                required=prop_name in required_names,
                description=prop_resolved.get("description"),
                location=location,
                enum_values=prop_resolved.get("enum"),
                format=prop_resolved.get("format"),
            )
        )

    return fields


def _parse_parameters(raw_parameters: List[Dict[str, Any]]) -> List[FieldSpec]:
    fields: List[FieldSpec] = []
    for raw_param in raw_parameters or []:
        param_schema = raw_param.get("schema", {}) or {}
        fields.append(
            FieldSpec(
                name=raw_param.get("name", "(unnamed parameter)"),
                type=param_schema.get("type", "string"),
                required=bool(raw_param.get("required", False)),
                description=raw_param.get("description"),
                location=raw_param.get("in", "query"),
                enum_values=param_schema.get("enum"),
                format=param_schema.get("format"),
            )
        )
    return fields


def _parse_responses(
    raw_responses: Dict[str, Any],
    components: Dict[str, Any],
) -> List[ResponseSpec]:
    responses: List[ResponseSpec] = []
    for status_code, raw_response in (raw_responses or {}).items():
        raw_response = raw_response or {}
        description = raw_response.get("description", "") or ""
        content = raw_response.get("content", {}) or {}
        json_content = content.get("application/json", {}) or {}
        schema = json_content.get("schema")
        fields = _fields_from_schema(schema, components, location="responseBody") if schema else []
        responses.append(
            ResponseSpec(status_code=str(status_code), description=description.strip(), fields=fields)
        )

    # Sort numerically where possible so 200 < 400 < 404 < 409 < 500, with
    # any non-numeric status codes (e.g. "default") sorted last.
    def sort_key(response: ResponseSpec):
        return (0, int(response.status_code)) if response.status_code.isdigit() else (1, response.status_code)

    return sorted(responses, key=sort_key)


def parse_spec(spec_path: str | Path) -> ParsedApiSpec:
    """Parses an OpenAPI 3.0 YAML file into a :class:`ParsedApiSpec`.

    Args:
        spec_path: Path to the OpenAPI YAML file.

    Returns:
        The parsed specification.

    Raises:
        ApiSpecError: If the file is missing, is not valid YAML, or is
            missing required OpenAPI sections (``info``, ``paths``).
    """
    spec_path = Path(spec_path)
    logger.info("Reading OpenAPI spec from %s", spec_path)
    document = _load_yaml(spec_path)

    if "openapi" not in document:
        raise ApiSpecError(
            f"'{spec_path}' does not look like an OpenAPI 3.x document "
            "(no top-level 'openapi' key was found)."
        )

    raw_info = document.get("info")
    if not isinstance(raw_info, dict) or "title" not in raw_info:
        raise ApiSpecError(
            f"'{spec_path}' has no usable 'info' section (an OpenAPI spec "
            "must declare at least info.title)."
        )

    raw_paths = document.get("paths")
    if not isinstance(raw_paths, dict) or not raw_paths:
        raise ApiSpecError(
            f"'{spec_path}' has no 'paths' section, so there are no "
            "endpoints to document."
        )

    components = document.get("components", {}) or {}

    info = ApiInfo(
        title=raw_info.get("title", "Untitled API"),
        version=str(raw_info.get("version", "0.0.0")),
        description=raw_info.get("description"),
    )

    operations: List[OperationSpec] = []
    for path, path_item in raw_paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in _HTTP_METHODS:
            if method not in path_item:
                continue
            raw_operation = path_item[method] or {}

            # Parameters may be declared at the path-item level (shared
            # across methods) and/or on the individual operation; both are
            # honored, per the OpenAPI spec.
            shared_params = path_item.get("parameters", []) or []
            own_params = raw_operation.get("parameters", []) or []
            parameters = _parse_parameters(shared_params + own_params)

            request_body = raw_operation.get("requestBody", {}) or {}
            request_content = request_body.get("content", {}) or {}
            request_json = request_content.get("application/json", {}) or {}
            request_schema = request_json.get("schema")
            request_fields = (
                _fields_from_schema(request_schema, components, location="requestBody")
                if request_schema
                else []
            )

            raw_responses = raw_operation.get("responses", {}) or {}
            if not raw_responses:
                raise ApiSpecError(
                    f"Operation '{method.upper()} {path}' in '{spec_path}' "
                    "documents no responses at all. Every operation must "
                    "document at least one response so error scenarios can "
                    "be captured for the requirements document."
                )
            responses = _parse_responses(raw_responses, components)

            operations.append(
                OperationSpec(
                    path=path,
                    method=method.upper(),
                    operation_id=raw_operation.get("operationId"),
                    summary=raw_operation.get("summary"),
                    description=raw_operation.get("description"),
                    parameters=parameters,
                    request_fields=request_fields,
                    request_required=bool(request_body.get("required", False)),
                    responses=responses,
                )
            )

    if not operations:
        raise ApiSpecError(
            f"'{spec_path}' declares one or more paths, but none of them "
            "have a recognized HTTP method (get/post/put/patch/delete/"
            "options/head/trace)."
        )

    # Stable, predictable ordering for the generated document: by path,
    # then by a conventional method ordering.
    method_order = {m.upper(): i for i, m in enumerate(_HTTP_METHODS)}
    operations.sort(key=lambda op: (op.path, method_order.get(op.method, 99)))

    logger.info(
        "Parsed %d operation(s) across %d path(s) from %s",
        len(operations),
        len(raw_paths),
        spec_path,
    )

    return ParsedApiSpec(info=info, operations=operations, source_path=str(spec_path))

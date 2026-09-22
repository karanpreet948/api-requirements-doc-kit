"""
apidoc.generator
=================

Renders a :class:`~apidoc.parser.ParsedApiSpec` into a Markdown "API
Integration Requirements Document" written in the style a Business
Analyst would hand to a development team (and that a non-technical
stakeholder could still follow): a short business-purpose statement per
endpoint, a request/response data-mapping table, a business-rules
section, and a structured error-scenario table built from the response
codes documented in the spec.

Where the OpenAPI spec's ``description`` fields do not carry enough
business context to explain *why* a field exists (as opposed to merely
its technical type), the generator inserts a clearly marked placeholder
-- ``[BA TO COMPLETE: business meaning of this field]`` -- so a reviewer
can see exactly what still needs a human Business Analyst's judgment
before the document is considered final.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from apidoc.parser import FieldSpec, OperationSpec, ParsedApiSpec, ResponseSpec

logger = logging.getLogger(__name__)

# Section headers are exposed as module-level constants so that both the
# generator and the test suite refer to exactly the same strings, rather
# than duplicating literal header text in two places.
DOCUMENT_TITLE_PREFIX = "# API Integration Requirements Document"
SECTION_OVERVIEW = "## 1. API Overview"
SECTION_ENDPOINT_SUMMARY = "## 2. Endpoint Summary"
SECTION_ENDPOINT_DETAILS = "## 3. Endpoint Requirements"
SUBSECTION_BUSINESS_PURPOSE = "#### Business Purpose"
SUBSECTION_REQUEST_MAPPING = "#### Request Data Mapping"
SUBSECTION_RESPONSE_MAPPING = "#### Response Data Mapping"
SUBSECTION_BUSINESS_RULES = "#### Business Rules"
SUBSECTION_ERROR_SCENARIOS = "#### Error Scenarios"

BA_PLACEHOLDER = "[BA TO COMPLETE: business meaning of this field]"
BA_RULE_PLACEHOLDER = (
    "[BA TO COMPLETE: describe any business rule, validation, or "
    "downstream effect associated with this operation, e.g. approval "
    "thresholds, notification triggers, or data retention requirements.]"
)
BA_ERROR_HANDLING_PLACEHOLDER = (
    "[BA TO COMPLETE: describe how the business expects this scenario to "
    "be handled, e.g. user-facing message, retry policy, or escalation.]"
)

# Human-readable explanations of common HTTP status codes, used to fill
# in the "meaning" column of the error-scenario table when the spec's own
# description is terse. The spec's description is always used for the
# "when it occurs" column; this table only supplies a plain-English label.
_STATUS_CODE_MEANINGS = {
    "200": "OK - Success",
    "201": "Created - Success",
    "202": "Accepted - Success (processing may continue asynchronously)",
    "204": "No Content - Success",
    "400": "Bad Request - Client/Validation Error",
    "401": "Unauthorized - Authentication Required",
    "403": "Forbidden - Not Permitted",
    "404": "Not Found",
    "409": "Conflict",
    "422": "Unprocessable Entity - Semantic Validation Error",
    "429": "Too Many Requests - Rate Limited",
    "500": "Internal Server Error",
    "502": "Bad Gateway",
    "503": "Service Unavailable",
}


def _status_meaning(status_code: str) -> str:
    return _STATUS_CODE_MEANINGS.get(status_code, "Unclassified status code")


def _escape_cell(text: Optional[str]) -> str:
    """Makes a string safe to place inside a single Markdown table cell."""
    if not text:
        return ""
    return text.replace("\n", " ").replace("|", "\\|").strip()


def _business_meaning(field_spec: FieldSpec) -> str:
    """Returns the description to show in the 'business meaning' column.

    If the spec's own description is detailed enough to be useful on its
    own, it is used as-is. Otherwise, the standard BA placeholder is
    appended so the gap is clearly flagged rather than silently filled
    with a guess.
    """
    description = _escape_cell(field_spec.description)
    if field_spec.has_business_context:
        return description
    if description:
        return f"{description} {BA_PLACEHOLDER}"
    return BA_PLACEHOLDER


def _render_field_table(fields: List[FieldSpec], empty_message: str) -> str:
    if not fields:
        return f"_{empty_message}_\n"

    lines = [
        "| Field | Type | Required? | Business Meaning |",
        "|---|---|---|---|",
    ]
    for f in fields:
        type_display = f.type
        if f.format:
            type_display = f"{type_display} ({f.format})"
        if f.enum_values:
            type_display = f"{type_display}, one of: {', '.join(str(v) for v in f.enum_values)}"
        lines.append(
            "| {name} | {type} | {required} | {meaning} |".format(
                name=_escape_cell(f.name),
                type=_escape_cell(type_display),
                required="Yes" if f.required else "No",
                meaning=_business_meaning(f),
            )
        )
    return "\n".join(lines) + "\n"


def _render_parameters_table(parameters: List[FieldSpec]) -> str:
    if not parameters:
        return "_This operation takes no path/query/header parameters._\n"

    lines = [
        "| Parameter | Location | Type | Required? | Business Meaning |",
        "|---|---|---|---|---|",
    ]
    for p in parameters:
        lines.append(
            "| {name} | {loc} | {type} | {required} | {meaning} |".format(
                name=_escape_cell(p.name),
                loc=p.location,
                type=_escape_cell(p.type),
                required="Yes" if p.required else "No",
                meaning=_business_meaning(p),
            )
        )
    return "\n".join(lines) + "\n"


def _render_error_table(responses: List[ResponseSpec]) -> str:
    error_responses = [r for r in responses if not r.is_success]
    if not error_responses:
        return "_This operation documents no error responses in the spec._\n"

    lines = [
        "| Status Code | Meaning | When It Occurs (per spec) | Business Handling |",
        "|---|---|---|---|",
    ]
    for r in error_responses:
        when_it_occurs = _escape_cell(r.description) or BA_PLACEHOLDER
        lines.append(
            "| {code} | {meaning} | {occurs} | {handling} |".format(
                code=r.status_code,
                meaning=_status_meaning(r.status_code),
                occurs=when_it_occurs,
                handling=BA_ERROR_HANDLING_PLACEHOLDER,
            )
        )
    return "\n".join(lines) + "\n"


def _render_endpoint_summary_table(operations: List[OperationSpec]) -> str:
    lines = [
        "| # | Method | Path | Summary |",
        "|---|---|---|---|",
    ]
    for i, op in enumerate(operations, start=1):
        lines.append(
            "| {i} | {method} | `{path}` | {summary} |".format(
                i=i,
                method=op.method,
                path=op.path,
                summary=_escape_cell(op.summary) or "_(no summary provided in spec)_",
            )
        )
    return "\n".join(lines) + "\n"


def _render_endpoint_section(op: OperationSpec, anchor_index: int) -> str:
    parts: List[str] = []
    parts.append(f"### {anchor_index}. {op.method} `{op.path}`\n")

    if op.operation_id:
        parts.append(f"_Operation ID: `{op.operation_id}`_\n")

    parts.append(SUBSECTION_BUSINESS_PURPOSE)
    purpose = (op.description or op.summary or "").strip()
    if purpose:
        parts.append(purpose + "\n")
    else:
        parts.append(
            f"{BA_PLACEHOLDER} (the OpenAPI spec provided no description "
            "or summary for this operation.)\n"
        )

    if op.parameters:
        parts.append("**Parameters**\n")
        parts.append(_render_parameters_table(op.parameters))

    parts.append(SUBSECTION_REQUEST_MAPPING)
    if op.request_fields:
        note = "Required in every request." if op.request_required else "Optional / partial update payload."
        parts.append(f"_{note}_\n")
        parts.append(_render_field_table(op.request_fields, "No request body fields documented."))
    else:
        parts.append("_This operation does not take a request body._\n")

    parts.append(SUBSECTION_RESPONSE_MAPPING)
    success = op.success_response
    if success:
        parts.append(f"_Primary success response: `{success.status_code}` - {_escape_cell(success.description) or '(no description provided)'}_\n")
        parts.append(_render_field_table(success.fields, "No response body fields documented for the success response."))
    else:
        parts.append("_No success (2xx) response is documented for this operation._\n")

    parts.append(SUBSECTION_BUSINESS_RULES)
    parts.append(BA_RULE_PLACEHOLDER + "\n")

    parts.append(SUBSECTION_ERROR_SCENARIOS)
    parts.append(_render_error_table(op.responses))

    return "\n".join(parts)


def generate_markdown(spec: ParsedApiSpec) -> str:
    """Renders a full requirements document for the given parsed spec.

    Args:
        spec: The parsed OpenAPI specification.

    Returns:
        The complete document as a single Markdown string.
    """
    logger.info(
        "Generating requirements document for '%s' (%d operations)",
        spec.info.title,
        len(spec.operations),
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    lines.append(f"{DOCUMENT_TITLE_PREFIX}: {spec.info.title}\n")
    lines.append(
        f"_Generated automatically by the API Requirements Documentation Kit "
        f"on {generated_at} from `{spec.source_path}`. Sections marked "
        f"`{BA_PLACEHOLDER}` require Business Analyst review before this "
        f"document is finalized._\n"
    )

    lines.append(SECTION_OVERVIEW)
    lines.append(f"- **API Title:** {spec.info.title}")
    lines.append(f"- **API Version:** {spec.info.version}")
    lines.append(f"- **Number of Endpoints Documented:** {len(spec.operations)}")
    if spec.info.description:
        lines.append("")
        lines.append(spec.info.description.strip())
    lines.append("")

    lines.append(SECTION_ENDPOINT_SUMMARY)
    lines.append(_render_endpoint_summary_table(spec.operations))

    lines.append(SECTION_ENDPOINT_DETAILS)
    for i, op in enumerate(spec.operations, start=1):
        lines.append(_render_endpoint_section(op, i))
        lines.append("")

    lines.append("---")
    lines.append(
        "_This document was generated from an OpenAPI specification and is "
        "intended as a starting point for a Business Analyst, not a "
        "finished deliverable. Every placeholder above must be reviewed "
        "and completed before this document is shared with a development "
        "team._"
    )

    return "\n".join(lines) + "\n"

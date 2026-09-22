"""Tests for apidoc.generator against the synthetic example spec."""

from pathlib import Path

from apidoc.generator import (
    BA_ERROR_HANDLING_PLACEHOLDER,
    BA_PLACEHOLDER,
    BA_RULE_PLACEHOLDER,
    DOCUMENT_TITLE_PREFIX,
    SECTION_ENDPOINT_DETAILS,
    SECTION_ENDPOINT_SUMMARY,
    SECTION_OVERVIEW,
    SUBSECTION_BUSINESS_PURPOSE,
    SUBSECTION_BUSINESS_RULES,
    SUBSECTION_ERROR_SCENARIOS,
    SUBSECTION_REQUEST_MAPPING,
    SUBSECTION_RESPONSE_MAPPING,
    generate_markdown,
)
from apidoc.parser import parse_spec

EXAMPLE_SPEC = Path(__file__).resolve().parent.parent / "examples" / "customer_profile_api.yaml"


def _generate():
    spec = parse_spec(EXAMPLE_SPEC)
    return generate_markdown(spec)


def test_document_has_all_expected_top_level_sections():
    document = _generate()
    assert DOCUMENT_TITLE_PREFIX in document
    assert "Customer Profile API" in document
    assert SECTION_OVERVIEW in document
    assert SECTION_ENDPOINT_SUMMARY in document
    assert SECTION_ENDPOINT_DETAILS in document


def test_document_has_one_full_subsection_set_per_endpoint():
    document = _generate()
    # Three endpoints in the example spec -> each subsection header should
    # appear at least three times (once per endpoint section).
    for header in (
        SUBSECTION_BUSINESS_PURPOSE,
        SUBSECTION_REQUEST_MAPPING,
        SUBSECTION_RESPONSE_MAPPING,
        SUBSECTION_BUSINESS_RULES,
        SUBSECTION_ERROR_SCENARIOS,
    ):
        assert document.count(header) == 3, f"Expected 3 occurrences of {header!r}"


def test_document_contains_data_mapping_table_header():
    document = _generate()
    assert "| Field | Type | Required? | Business Meaning |" in document


def test_document_contains_error_scenario_table_header():
    document = _generate()
    assert "| Status Code | Meaning | When It Occurs (per spec) | Business Handling |" in document
    # Every documented status code from the example spec should show up
    # somewhere in an error table.
    for code in ("400", "404", "409", "500"):
        assert f"| {code} |" in document


def test_document_flags_business_rule_placeholders():
    document = _generate()
    assert BA_RULE_PLACEHOLDER in document
    assert BA_ERROR_HANDLING_PLACEHOLDER in document


def test_document_flags_thin_field_descriptions_with_ba_placeholder():
    document = _generate()
    # The example spec intentionally gives every field a real description,
    # but the placeholder mechanism itself must still work end-to-end, so
    # we exercise it directly against a minimal synthetic spec here rather
    # than relying on a gap in the (deliberately complete) example file.
    from apidoc.parser import FieldSpec, OperationSpec, ApiInfo, ParsedApiSpec, ResponseSpec

    thin_field = FieldSpec(
        name="internalFlag",
        type="boolean",
        required=False,
        description="Flag.",  # too short to count as real business context
        location="responseBody",
    )
    op = OperationSpec(
        path="/widgets/{id}",
        method="GET",
        operation_id="getWidget",
        summary="Get a widget",
        description="Retrieves a widget.",
        responses=[ResponseSpec(status_code="200", description="OK", fields=[thin_field])],
    )
    spec = ParsedApiSpec(
        info=ApiInfo(title="Widget API", version="1.0.0"),
        operations=[op],
        source_path="synthetic-in-memory-spec.yaml",
    )
    doc = generate_markdown(spec)
    assert BA_PLACEHOLDER in doc


def test_document_is_deterministic_in_structure_across_runs():
    first = _generate()
    second = _generate()
    # Timestamps differ, so strip the generated-at line before comparing.
    def strip_timestamp(text):
        return "\n".join(line for line in text.splitlines() if not line.startswith("_Generated automatically"))

    assert strip_timestamp(first) == strip_timestamp(second)

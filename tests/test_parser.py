"""Tests for apidoc.parser against the synthetic example spec."""

from pathlib import Path

import pytest

from apidoc.parser import ApiSpecError, parse_spec

EXAMPLE_SPEC = Path(__file__).resolve().parent.parent / "examples" / "customer_profile_api.yaml"


def test_example_spec_exists():
    assert EXAMPLE_SPEC.exists(), f"Expected example spec at {EXAMPLE_SPEC}"


def test_parses_info_block():
    spec = parse_spec(EXAMPLE_SPEC)
    assert spec.info.title == "Customer Profile API"
    assert spec.info.version == "1.2.0"
    assert spec.info.description  # non-empty


def test_extracts_expected_number_of_operations():
    spec = parse_spec(EXAMPLE_SPEC)
    # GET /customers/{id}, PATCH /customers/{id}, POST /customers
    assert len(spec.operations) == 3
    display_names = {op.display_name for op in spec.operations}
    assert display_names == {
        "GET /customers/{id}",
        "PATCH /customers/{id}",
        "POST /customers",
    }


def _find(spec, method, path):
    for op in spec.operations:
        if op.method == method and op.path == path:
            return op
    raise AssertionError(f"No operation found for {method} {path}")


def test_get_customer_by_id_operation_shape():
    spec = parse_spec(EXAMPLE_SPEC)
    op = _find(spec, "GET", "/customers/{id}")

    assert op.operation_id == "getCustomerById"
    assert op.description  # has a business description

    # path param 'id' + query param 'includeArchived'
    assert len(op.parameters) == 2
    param_names = {p.name for p in op.parameters}
    assert param_names == {"id", "includeArchived"}

    # No request body on a GET
    assert op.request_fields == []

    # CustomerProfile schema has 11 top-level properties
    success = op.success_response
    assert success is not None
    assert success.status_code == "200"
    assert len(success.fields) == 11

    # Documented error responses: 400, 404, 500
    error_codes = {r.status_code for r in op.error_responses}
    assert error_codes == {"400", "404", "500"}


def test_create_customer_operation_shape():
    spec = parse_spec(EXAMPLE_SPEC)
    op = _find(spec, "POST", "/customers")

    assert op.operation_id == "createCustomer"
    assert op.request_required is True

    # CustomerProfileCreateRequest has 7 properties, 3 required
    assert len(op.request_fields) == 7
    required_fields = {f.name for f in op.request_fields if f.required}
    assert required_fields == {"firstName", "lastName", "emailAddress"}

    success = op.success_response
    assert success is not None
    assert success.status_code == "201"
    assert len(success.fields) == 11

    error_codes = {r.status_code for r in op.error_responses}
    assert error_codes == {"400", "409", "500"}


def test_update_customer_operation_shape():
    spec = parse_spec(EXAMPLE_SPEC)
    op = _find(spec, "PATCH", "/customers/{id}")

    assert op.operation_id == "updateCustomerById"
    assert len(op.parameters) == 1
    assert op.parameters[0].name == "id"
    assert op.parameters[0].required is True

    # CustomerProfileUpdateRequest has 4 optional properties
    assert len(op.request_fields) == 4
    assert all(not f.required for f in op.request_fields)

    error_codes = {r.status_code for r in op.error_responses}
    assert error_codes == {"400", "404", "409", "500"}


def test_missing_file_raises_clear_error(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ApiSpecError, match="not found"):
        parse_spec(missing)


def test_invalid_yaml_raises_clear_error(tmp_path):
    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("openapi: 3.0.3\ninfo: [this is not, a mapping\n", encoding="utf-8")
    with pytest.raises(ApiSpecError):
        parse_spec(bad_file)


def test_missing_paths_section_raises_clear_error(tmp_path):
    incomplete = tmp_path / "incomplete.yaml"
    incomplete.write_text(
        "openapi: 3.0.3\ninfo:\n  title: Incomplete API\n  version: '1.0'\n",
        encoding="utf-8",
    )
    with pytest.raises(ApiSpecError, match="paths"):
        parse_spec(incomplete)


def test_missing_info_section_raises_clear_error(tmp_path):
    incomplete = tmp_path / "no_info.yaml"
    incomplete.write_text(
        "openapi: 3.0.3\npaths:\n  /widgets:\n    get:\n      responses:\n        '200':\n          description: ok\n",
        encoding="utf-8",
    )
    with pytest.raises(ApiSpecError, match="info"):
        parse_spec(incomplete)


def test_unresolvable_ref_raises_clear_error(tmp_path):
    bad_ref = tmp_path / "bad_ref.yaml"
    bad_ref.write_text(
        """
openapi: 3.0.3
info:
  title: Bad Ref API
  version: '1.0'
paths:
  /widgets:
    get:
      responses:
        '200':
          description: ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DoesNotExist'
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ApiSpecError, match="DoesNotExist"):
        parse_spec(bad_ref)


def test_operation_with_no_responses_raises_clear_error(tmp_path):
    bad_spec = tmp_path / "no_responses.yaml"
    bad_spec.write_text(
        """
openapi: 3.0.3
info:
  title: No Responses API
  version: '1.0'
paths:
  /widgets:
    get:
      responses: {}
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ApiSpecError, match="responses"):
        parse_spec(bad_spec)

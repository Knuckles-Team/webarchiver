import json

import pytest

from webarchiver.error_authority import (
    BROWSER_HTML_MEDIA_TYPE,
    MAX_DETAIL_CHARS,
    PROBLEM_JSON_MEDIA_TYPE,
    STRUCTURED_MARKDOWN_MEDIA_TYPE,
    ProblemDetails,
    render_error,
)


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_agent_representations_share_metadata():
    problem = ProblemDetails(
        status=503,
        code="dependency_unavailable",
        type_uri="urn:agent-error:dependency-unavailable",
        instance="urn:request:abc123",
        detail="The upstream is temporarily unavailable.",
        retryable=True,
        retry_after_s=12,
    )
    json_response = render_error(problem, accept=PROBLEM_JSON_MEDIA_TYPE)
    markdown_response = render_error(problem, accept=STRUCTURED_MARKDOWN_MEDIA_TYPE)
    payload = json.loads(json_response.body)

    assert json_response.media_type == PROBLEM_JSON_MEDIA_TYPE
    assert markdown_response.media_type == STRUCTURED_MARKDOWN_MEDIA_TYPE
    assert json_response.headers["Vary"] == "Accept"
    assert json_response.headers["Retry-After"] == "12.0"
    for field, value in problem.metadata().items():
        assert payload[field] == value
        assert field + ": " + json.dumps(value) in markdown_response.body


def test_denial_is_never_retryable_and_detail_is_bounded():
    denied = ProblemDetails(
        status=403,
        code="permission_denied",
        instance="urn:request:denied",
        detail=("/home/operator/private-token " + ("x" * (MAX_DETAIL_CHARS + 100))),
        retryable=True,
        retry_after_s=30,
    )
    response = render_error(denied, accept=PROBLEM_JSON_MEDIA_TYPE)
    payload = json.loads(response.body)

    assert payload["retryable"] is False
    assert payload["retry_after_s"] is None
    assert len(payload["detail"]) <= MAX_DETAIL_CHARS
    assert "/home/operator" not in payload["detail"]


def test_browser_html_is_retained_for_browser_accept_headers():
    problem = ProblemDetails(
        status=400,
        code="invalid_request",
        instance="urn:request:browser",
        detail="The request is invalid.",
    )
    response = render_error(problem, accept="text/html,application/xhtml+xml")

    assert response.media_type == BROWSER_HTML_MEDIA_TYPE
    assert response.body.startswith("<!doctype html>")
    assert 'data-error-code="invalid_request"' in response.body

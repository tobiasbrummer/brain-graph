from __future__ import annotations

from brain_graph.utils.cli_utils import error_result, ok_result


def test_ok_result_has_standard_fields() -> None:
    payload = ok_result("tool_x", answer=42)

    assert payload["ok"] is True
    assert payload["tool"] == "tool_x"
    assert payload["status"] == "ok"
    assert "ts" in payload
    assert payload["answer"] == 42


def test_error_result_includes_exception_details() -> None:
    try:
        raise ValueError("boom")
    except Exception as exc:
        payload = error_result("tool_y", exc, include_traceback=True)

    assert payload["ok"] is False
    assert payload["tool"] == "tool_y"
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "ValueError"
    assert payload["error"]["message"] == "boom"
    assert "traceback" in payload["error"]

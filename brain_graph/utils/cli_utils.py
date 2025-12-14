from __future__ import annotations

import json
import sys
import time
import traceback as tb
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ms_since(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def emit_json(payload: Any, *, pretty: bool = False) -> None:
    if pretty:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    else:
        json.dump(payload, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


def ok_result(tool: str, *, status: str = "ok", **fields: Any) -> dict[str, Any]:
    return {"ok": True, "tool": tool, "status": status, "ts": utc_now_iso(), **fields}


def error_result(
    tool: str,
    exc: BaseException,
    *,
    status: str = "error",
    include_traceback: bool = False,
    **fields: Any,
) -> dict[str, Any]:
    error: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)}
    if include_traceback:
        error["traceback"] = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
    return {"ok": False, "tool": tool, "status": status, "ts": utc_now_iso(), "error": error, **fields}


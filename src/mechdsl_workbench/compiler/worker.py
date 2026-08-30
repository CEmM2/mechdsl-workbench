"""JSON-over-stdio worker used for isolated MechDSL calls."""

from __future__ import annotations

import contextlib
import json
import sys
from typing import Any

from .backend import LocalMechDSLBackend
from .diagnostics import normalize_exception
from .models import (
    CompileRequest,
    TranspileRequest,
    compile_success,
    transpile_success,
    workbench_failure,
)


def handle_payload(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    backend = LocalMechDSLBackend()

    try:
        # Keep the worker protocol on stdout clean even if a dependency prints.
        with contextlib.redirect_stdout(sys.stderr):
            if action == "compile":
                request_data = _request_object(payload, action)
                request = CompileRequest.from_mapping(request_data)
                raw = backend.compile(request)
                return compile_success(
                    emitted_source=raw["emitted_source"],
                    element_ir_summary=raw["element_ir_summary"],
                    content_hash=raw["content_hash"],
                    derived_energy_present=raw["derived_energy_present"],
                )

            if action == "transpile":
                request_data = _request_object(payload, action)
                request = TranspileRequest.from_mapping(request_data)
                raw = backend.transpile(request)
                return transpile_success(
                    code=raw["code"],
                    entry_point=raw["entry_point"],
                    line_count=raw["line_count"],
                    valid_python=raw["valid_python"],
                    backend=request.backend,
                )

            if action == "capabilities":
                return {
                    "ok": True,
                    "capabilities": backend.capabilities(),
                    "packages": backend.package_versions(),
                }

            if action == "models":
                return {"ok": True, "models": backend.models()}

            raise ValueError(f"unsupported worker action: {action!r}")
    except Exception as exc:  # worker boundary: normalize, do not leak a traceback by default
        return workbench_failure(normalize_exception(exc, source=_payload_source(payload)))


def _request_object(payload: dict[str, Any], action: object) -> dict[str, Any]:
    request_data = payload.get("request")
    if not isinstance(request_data, dict):
        raise TypeError(f"{action} action requires a request object")
    return request_data


def _payload_source(payload: dict[str, Any]) -> str | None:
    request_data = payload.get("request")
    if not isinstance(request_data, dict):
        return None
    for key in ("problem_source", "algorithm_source", "energy_source"):
        value = request_data.get(key)
        if isinstance(value, str):
            return value
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise TypeError("worker input must be a JSON object")
        result = handle_payload(payload)
    except Exception as exc:
        result = workbench_failure(normalize_exception(exc))

    json.dump(result, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Local request/result models for the workbench compiler boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

Severity = Literal["error", "warning", "info"]
WorkbenchMode = Literal["mechanics", "algorithm"]


@dataclass(frozen=True, slots=True)
class CompileRequest:
    """Request sent to ``mechdsl.integration.compile_from_sources``."""

    problem_source: str
    energy_source: str | None = None
    profile: str = "mvp"

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_source": self.problem_source,
            "energy_source": self.energy_source,
            "profile": self.profile,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> CompileRequest:
        problem_source = data.get("problem_source")
        energy_source = data.get("energy_source")
        profile = data.get("profile", "mvp")

        if not isinstance(problem_source, str):
            raise TypeError("problem_source must be a string")
        if energy_source is not None and not isinstance(energy_source, str):
            raise TypeError("energy_source must be a string or null")
        if not isinstance(profile, str) or not profile.strip():
            raise TypeError("profile must be a non-empty string")

        return cls(
            problem_source=problem_source,
            energy_source=energy_source,
            profile=profile,
        )


@dataclass(frozen=True, slots=True)
class TranspileRequest:
    """Request sent to ``mechdsl.integration.transpile_algorithm``."""

    algorithm_source: str
    backend: str = "taichi"

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm_source": self.algorithm_source,
            "backend": self.backend,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> TranspileRequest:
        algorithm_source = data.get("algorithm_source")
        backend = data.get("backend", "taichi")

        if not isinstance(algorithm_source, str):
            raise TypeError("algorithm_source must be a string")
        if not isinstance(backend, str) or not backend.strip():
            raise TypeError("backend must be a non-empty string")

        return cls(algorithm_source=algorithm_source, backend=backend)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: Severity
    stage: str
    category: str
    message: str
    code: str | None = None
    line: int | None = None
    column: int | None = None
    source_excerpt: str | None = None
    technical_details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "stage": self.stage,
            "category": self.category,
            "message": self.message,
            "code": self.code,
            "line": self.line,
            "column": self.column,
            "source_excerpt": self.source_excerpt,
            "technical_details": self.technical_details,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Diagnostic:
        severity = data.get("severity", "error")
        if severity not in {"error", "warning", "info"}:
            severity = "error"
        return cls(
            severity=severity,
            stage=str(data.get("stage", "unknown")),
            category=str(data.get("category", "CompilerError")),
            message=str(data.get("message", "Unknown compiler failure")),
            code=_optional_str(data.get("code")),
            line=_optional_int(data.get("line")),
            column=_optional_int(data.get("column")),
            source_excerpt=_optional_str(data.get("source_excerpt")),
            technical_details=_optional_str(data.get("technical_details")),
        )


def compile_success(
    *,
    emitted_source: str,
    element_ir_summary: Mapping[str, Any],
    content_hash: str,
    derived_energy_present: bool,
) -> dict[str, Any]:
    """Return the stable workbench response for a mechanics compilation."""

    return {
        "ok": True,
        "result_kind": "compile",
        "mode": "mechanics",
        "generated_source": emitted_source,
        "emitted_source": emitted_source,
        "element_ir_summary": dict(element_ir_summary),
        "content_hash": content_hash,
        "derived_energy_present": derived_energy_present,
    }


def transpile_success(
    *,
    code: str,
    entry_point: str,
    line_count: int,
    valid_python: bool,
    backend: str,
) -> dict[str, Any]:
    """Return the stable workbench response for an algo2code transpilation."""

    return {
        "ok": True,
        "result_kind": "transpile",
        "mode": "algorithm",
        "generated_source": code,
        "code": code,
        "entry_point": entry_point,
        "line_count": line_count,
        "valid_python": valid_python,
        "backend": backend,
    }


def workbench_failure(diagnostic: Diagnostic) -> dict[str, Any]:
    return {"ok": False, "diagnostic": diagnostic.to_dict()}


# Backward-compatible internal alias retained for v0.1 fixtures and callers.
compile_failure = workbench_failure


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

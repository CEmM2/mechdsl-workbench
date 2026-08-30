"""Normalize compiler and worker exceptions for presentation in the UI."""

from __future__ import annotations

from typing import Any

from .models import Diagnostic


def normalize_exception(
    exc: BaseException,
    *,
    source: str | None = None,
    technical_details: str | None = None,
) -> Diagnostic:
    """Convert an arbitrary exception into a stable workbench diagnostic.

    Location data is read only from explicit exception attributes. The function
    deliberately does not scrape exception text to guess a line or column.
    """

    category = type(exc).__name__
    module = type(exc).__module__
    stage, code = _classify_exception(category, module)
    line = _first_int_attr(exc, "line", "lineno", "line_no")
    column = _first_int_attr(exc, "column", "col", "colno", "offset")

    message = str(exc).strip() or category
    excerpt = build_source_excerpt(source, line, column) if source and line else None

    return Diagnostic(
        severity="error",
        stage=stage,
        category=category,
        message=message,
        code=code,
        line=line,
        column=column,
        source_excerpt=excerpt,
        technical_details=technical_details,
    )


def build_source_excerpt(
    source: str,
    line: int,
    column: int | None = None,
    *,
    context_lines: int = 2,
) -> str:
    lines = source.splitlines()
    if line < 1 or line > len(lines):
        return ""

    start = max(1, line - context_lines)
    end = min(len(lines), line + context_lines)
    width = len(str(end))
    rendered: list[str] = []

    for number in range(start, end + 1):
        marker = ">" if number == line else " "
        rendered.append(f"{marker} {number:>{width}} | {lines[number - 1]}")
        if number == line and column is not None and column > 0:
            prefix = " " * (width + 5 + column - 1)
            rendered.append(f"{prefix}^")

    return "\n".join(rendered)


def worker_diagnostic(
    *,
    category: str,
    message: str,
    technical_details: str | None = None,
    code: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        severity="error",
        stage="worker",
        category=category,
        message=message,
        code=code,
        technical_details=technical_details,
    )


def _classify_exception(category: str, module: str) -> tuple[str, str | None]:
    lowered = category.lower()
    module_lower = module.lower()

    if category in {"ModuleNotFoundError", "ImportError", "BackendUnavailable"}:
        return "environment", "WORKBENCH-ENV-001"
    if "parse" in lowered or "frontend" in module_lower:
        return "frontend", "MECHDSL-FRONTEND"
    if "unsupported" in lowered or "semantic" in lowered:
        return "validation", "MECHDSL-VALIDATION"
    if category in {"ValueError", "TypeError"}:
        return "input", "WORKBENCH-INPUT-001"
    if "timeout" in lowered:
        return "worker", "WORKBENCH-WORKER-TIMEOUT"
    return "compiler", None


def _first_int_attr(exc: BaseException, *names: str) -> int | None:
    for name in names:
        value: Any = getattr(exc, name, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None

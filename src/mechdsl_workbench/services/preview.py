"""Safe presentational previews for mechanics and algorithm LaTeX sources."""

from __future__ import annotations

import html
import shlex
from dataclasses import dataclass
from typing import Any, Literal

PreviewMode = Literal["mechanics", "algorithm"]


@dataclass(frozen=True, slots=True)
class DirectivePreview:
    kind: str
    title: str
    summary: str
    raw: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "raw": self.raw,
        }


def render_preview(source: str, *, mode: PreviewMode = "mechanics") -> dict[str, Any]:
    if mode == "mechanics":
        return _render_mechanics_preview(source)
    if mode == "algorithm":
        return _render_algorithm_preview(source)
    raise ValueError(f"unsupported preview mode: {mode!r}")


def _render_mechanics_preview(source: str) -> dict[str, Any]:
    directives: list[DirectivePreview] = []
    body_lines: list[str] = []
    warnings: list[str] = []

    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("% mechanics"):
            try:
                directives.append(parse_mechanics_directive(stripped))
            except ValueError as exc:
                warnings.append(f"Line {line_number}: {exc}")
            continue
        if stripped.startswith("%"):
            continue
        body_lines.append(line)

    return {
        "mode": "mechanics",
        "body_html": _safe_document_html("\n".join(body_lines)),
        "directives": [directive.to_dict() for directive in directives],
        "directive_heading": "Mechanics directives",
        "empty_directive_message": "No % mechanics directives found.",
        "warnings": warnings,
        "note": (
            "This is a presentational browser preview. The Translation View is the source "
            "of truth for what MechDSL actually understood."
        ),
    }


def _render_algorithm_preview(source: str) -> dict[str, Any]:
    directives: list[DirectivePreview] = []
    body_lines: list[str] = []
    warnings: list[str] = []
    recognized = {"algorithm", "backend", "args", "type"}

    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("%"):
            payload = stripped[1:].strip()
            kind = payload.split(maxsplit=1)[0] if payload else ""
            if kind in recognized:
                try:
                    directives.append(parse_algorithm_directive(stripped))
                except ValueError as exc:
                    warnings.append(f"Line {line_number}: {exc}")
            continue
        body_lines.append(line)

    if not any(directive.kind == "algorithm" for directive in directives):
        warnings.append("No % algorithm name directive was found.")
    if "\\begin{algorithmic}" not in source or "\\end{algorithmic}" not in source:
        warnings.append("The source does not contain a complete algorithmic environment.")

    return {
        "mode": "algorithm",
        "body_html": _safe_algorithm_html("\n".join(body_lines)),
        "directives": [directive.to_dict() for directive in directives],
        "directive_heading": "Algorithm contract",
        "empty_directive_message": "No algo2code directives found.",
        "warnings": warnings,
        "note": (
            "The preview shows the authored algpseudocode safely. The Translation View reports "
            "the entry point and Python-validity result returned by algo2code."
        ),
    }


def parse_mechanics_directive(line: str) -> DirectivePreview:
    prefix = "% mechanics"
    if not line.strip().startswith(prefix):
        raise ValueError("not a mechanics directive")

    payload = line.strip()[len(prefix) :].strip()
    if not payload:
        raise ValueError("empty % mechanics directive")

    tokens = shlex.split(payload)
    if not tokens:
        raise ValueError("empty % mechanics directive")

    kind = tokens[0]
    args = tokens[1:]
    options = _parse_options(args)

    title_map = {
        "dim": "Dimension",
        "cell": "Element",
        "formulation": "Formulation",
        "material": "Material",
        "field": "Field",
        "constitutive": "Constitutive role",
        "weak_form": "Weak form",
        "boundary": "Boundary condition",
    }
    title = title_map.get(kind, kind.replace("_", " ").title())
    summary = _summarize_mechanics(kind, args, options)
    return DirectivePreview(kind=kind, title=title, summary=summary, raw=line)


# v0.1 imported this name in a few downstream notebooks. Kept as a harmless alias.
parse_directive = parse_mechanics_directive


def parse_algorithm_directive(line: str) -> DirectivePreview:
    stripped = line.strip()
    if not stripped.startswith("%"):
        raise ValueError("not an algorithm directive")
    payload = stripped[1:].strip()
    if not payload:
        raise ValueError("empty algorithm directive")

    tokens = shlex.split(payload)
    if not tokens:
        raise ValueError("empty algorithm directive")
    kind, args = tokens[0], tokens[1:]
    if kind not in {"algorithm", "backend", "args", "type"}:
        raise ValueError(f"unsupported algorithm directive: %{kind}")

    title_map = {
        "algorithm": "Entry point",
        "backend": "Backend",
        "args": "Arguments",
        "type": "Scratch type",
    }
    if kind == "type" and len(args) >= 2:
        summary = f"{args[0]}: {args[1]}"
    else:
        summary = " ".join(args) or "unspecified"
    return DirectivePreview(kind=kind, title=title_map[kind], summary=summary, raw=line)


def _parse_options(tokens: list[str]) -> dict[str, str | bool]:
    options: dict[str, str | bool] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            index += 1
            continue
        key = token[2:]
        values: list[str] = []
        index += 1
        while index < len(tokens) and not tokens[index].startswith("--"):
            values.append(tokens[index])
            index += 1
        options[key] = " ".join(values) if values else True
    return options


def _summarize_mechanics(
    kind: str,
    args: list[str],
    options: dict[str, str | bool],
) -> str:
    positional = [token for token in args if not token.startswith("--")]
    head = positional[0] if positional else ""

    if kind in {"dim", "cell", "formulation"}:
        return head or "unspecified"
    if kind == "material":
        params = ", ".join(f"{key}={value}" for key, value in options.items())
        return f"{head}{f' ({params})' if params else ''}"
    if kind == "boundary":
        boundary_type = options.get("type", "unspecified")
        surface = options.get("surface")
        suffix = f", surface={surface}" if surface else ""
        return f"{head or 'unnamed'}: {boundary_type}{suffix}"
    if kind in {"field", "constitutive", "weak_form"}:
        detail = ", ".join(f"{key}={value}" for key, value in options.items())
        return f"{head}{f' ({detail})' if detail else ''}"
    return " ".join(args) or "unspecified"


def _safe_document_html(source: str) -> str:
    escaped = html.escape(source, quote=True)
    if not escaped.strip():
        return '<p class="preview-empty">No non-comment LaTeX body was found.</p>'

    paragraphs: list[str] = []
    for block in escaped.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        paragraphs.append(f"<p>{stripped.replace(chr(10), '<br>')}</p>")
    return '<div class="latex-preview-body">' + "".join(paragraphs) + "</div>"


def _safe_algorithm_html(source: str) -> str:
    escaped = html.escape(source, quote=True)
    if not escaped.strip():
        return '<p class="preview-empty">No algorithmic body was found.</p>'
    return f'<pre class="algorithm-source-preview"><code>{escaped}</code></pre>'

from __future__ import annotations

import pytest

from mechdsl_workbench.services.preview import (
    parse_algorithm_directive,
    parse_mechanics_directive,
    render_preview,
)

pytestmark = pytest.mark.unit


def test_mechanics_preview_extracts_directives_and_body() -> None:
    source = """% mechanics dim 3
% mechanics cell hex8

Energy $\\Psi$.
"""
    preview = render_preview(source, mode="mechanics")
    assert [item["kind"] for item in preview["directives"]] == ["dim", "cell"]
    assert "Energy" in preview["body_html"]
    assert "% mechanics" not in preview["body_html"]


def test_algorithm_preview_extracts_contract_and_body() -> None:
    source = r"""% algorithm axpy
% backend taichi
% args a:scalar, x:vector, y:vector
% type z vector
\begin{algorithmic}
\State $z = a \cdot x + y$
\Return $z$
\end{algorithmic}
"""
    preview = render_preview(source, mode="algorithm")
    assert [item["kind"] for item in preview["directives"]][:3] == [
        "algorithm",
        "backend",
        "args",
    ]
    assert "algorithmic" in preview["body_html"]
    assert preview["directive_heading"] == "Algorithm contract"
    assert preview["warnings"] == []


def test_preview_escapes_user_html_in_both_modes() -> None:
    for mode in ("mechanics", "algorithm"):
        preview = render_preview('<script>alert("x")</script>', mode=mode)
        assert "<script>" not in preview["body_html"]
        assert "&lt;script&gt;" in preview["body_html"]


def test_material_directive_summary() -> None:
    directive = parse_mechanics_directive("% mechanics material svk --E 200e3 --nu 0.3")
    assert directive.title == "Material"
    assert "svk" in directive.summary
    assert "E=200e3" in directive.summary


def test_algorithm_type_directive_summary() -> None:
    directive = parse_algorithm_directive("% type residual scalar")
    assert directive.title == "Scratch type"
    assert directive.summary == "residual: scalar"


def test_malformed_quoted_mechanics_directive_becomes_warning() -> None:
    preview = render_preview('% mechanics boundary load --traction "unterminated')
    assert preview["directives"] == []
    assert preview["warnings"]


def test_algorithm_preview_warns_about_incomplete_environment() -> None:
    preview = render_preview("% algorithm incomplete", mode="algorithm")
    assert any("complete algorithmic environment" in warning for warning in preview["warnings"])

from __future__ import annotations

import pytest

from mechdsl_workbench.compiler.models import (
    CompileRequest,
    Diagnostic,
    TranspileRequest,
    compile_success,
    transpile_success,
)

pytestmark = pytest.mark.unit


def test_compile_request_round_trip() -> None:
    request = CompileRequest(problem_source="% mechanics dim 3", energy_source=None)
    assert CompileRequest.from_mapping(request.to_dict()) == request


def test_compile_request_rejects_non_string_source() -> None:
    with pytest.raises(TypeError, match="problem_source"):
        CompileRequest.from_mapping({"problem_source": 3})


def test_transpile_request_round_trip() -> None:
    request = TranspileRequest(algorithm_source=r"\begin{algorithmic}\end{algorithmic}")
    assert TranspileRequest.from_mapping(request.to_dict()) == request


def test_transpile_request_rejects_empty_backend() -> None:
    with pytest.raises(TypeError, match="backend"):
        TranspileRequest.from_mapping({"algorithm_source": "x", "backend": ""})


def test_compile_success_has_generic_and_specific_source_keys() -> None:
    result = compile_success(
        emitted_source="pass\n",
        element_ir_summary={},
        content_hash="a" * 64,
        derived_energy_present=False,
    )
    assert result["generated_source"] == result["emitted_source"]
    assert result["mode"] == "mechanics"


def test_transpile_success_has_generic_and_specific_source_keys() -> None:
    result = transpile_success(
        code="pass\n",
        entry_point="demo",
        line_count=1,
        valid_python=True,
        backend="taichi",
    )
    assert result["generated_source"] == result["code"]
    assert result["mode"] == "algorithm"


def test_diagnostic_round_trip() -> None:
    diagnostic = Diagnostic(
        severity="error",
        stage="frontend",
        category="ParseError",
        message="bad token",
        line=4,
        column=2,
    )
    assert Diagnostic.from_mapping(diagnostic.to_dict()) == diagnostic

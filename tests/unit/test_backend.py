from __future__ import annotations

from types import SimpleNamespace

import pytest

from mechdsl_workbench.compiler.backend import BackendContractError, LocalMechDSLBackend
from mechdsl_workbench.compiler.models import CompileRequest, TranspileRequest

pytestmark = pytest.mark.unit


def test_backend_calls_only_public_compile_facade(monkeypatch) -> None:
    calls = {}

    def compile_from_sources(**kwargs):
        calls.update(kwargs)
        return {
            "element_ir_summary": {},
            "emitted_source": "pass\n",
            "content_hash": "a" * 64,
            "derived_energy_present": False,
        }

    integration = SimpleNamespace(compile_from_sources=compile_from_sources)
    monkeypatch.setattr(LocalMechDSLBackend, "_integration", staticmethod(lambda: integration))
    result = LocalMechDSLBackend().compile(CompileRequest(problem_source="source"))
    assert result["emitted_source"] == "pass\n"
    assert calls["problem_source"] == "source"


def test_backend_calls_public_transpile_facade(monkeypatch) -> None:
    calls = {}

    def transpile_algorithm(source, backend):
        calls["source"] = source
        calls["backend"] = backend
        return {
            "code": "def demo():\n    pass\n",
            "entry_point": "demo",
            "line_count": 2,
            "valid_python": True,
        }

    integration = SimpleNamespace(transpile_algorithm=transpile_algorithm)
    monkeypatch.setattr(LocalMechDSLBackend, "_integration", staticmethod(lambda: integration))
    result = LocalMechDSLBackend().transpile(TranspileRequest(algorithm_source="latex"))
    assert result["entry_point"] == "demo"
    assert calls == {"source": "latex", "backend": "taichi"}


def test_backend_rejects_malformed_transpile_result(monkeypatch) -> None:
    integration = SimpleNamespace(transpile_algorithm=lambda *_args, **_kwargs: {"code": "pass"})
    monkeypatch.setattr(LocalMechDSLBackend, "_integration", staticmethod(lambda: integration))
    with pytest.raises(BackendContractError, match="missing keys"):
        LocalMechDSLBackend().transpile(TranspileRequest(algorithm_source="latex"))


def test_package_versions_report_missing_distribution_as_none(monkeypatch) -> None:
    from importlib import metadata

    def fake_version(name: str) -> str:
        if name == "mechdsl-core":
            return "0.2.0"
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", fake_version)
    assert LocalMechDSLBackend().package_versions() == {
        "mechdsl-core": "0.2.0",
        "algo2code": None,
    }

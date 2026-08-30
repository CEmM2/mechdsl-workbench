from __future__ import annotations

import pytest

from mechdsl_workbench.compiler import worker

pytestmark = pytest.mark.unit


class FakeBackend:
    def compile(self, request):
        return {
            "emitted_source": "pass\n",
            "element_ir_summary": {},
            "content_hash": "a" * 64,
            "derived_energy_present": False,
        }

    def transpile(self, request):
        return {
            "code": "def demo():\n    pass\n",
            "entry_point": "demo",
            "line_count": 2,
            "valid_python": True,
        }

    def capabilities(self):
        return {"version": "0.2.0"}

    def package_versions(self):
        return {"mechdsl-core": "0.2.0", "algo2code": "0.2.0"}

    def models(self):
        return [{"name": "svk"}]


def test_worker_compile_action(monkeypatch) -> None:
    monkeypatch.setattr(worker, "LocalMechDSLBackend", FakeBackend)
    result = worker.handle_payload(
        {"action": "compile", "request": {"problem_source": "% mechanics dim 3"}}
    )
    assert result["ok"] is True
    assert result["result_kind"] == "compile"


def test_worker_transpile_action(monkeypatch) -> None:
    monkeypatch.setattr(worker, "LocalMechDSLBackend", FakeBackend)
    result = worker.handle_payload(
        {"action": "transpile", "request": {"algorithm_source": "% algorithm demo"}}
    )
    assert result["ok"] is True
    assert result["result_kind"] == "transpile"
    assert result["entry_point"] == "demo"


def test_worker_capabilities_include_package_versions(monkeypatch) -> None:
    monkeypatch.setattr(worker, "LocalMechDSLBackend", FakeBackend)
    result = worker.handle_payload({"action": "capabilities"})
    assert result["ok"] is True
    assert result["packages"]["algo2code"] == "0.2.0"


def test_worker_normalizes_bad_action(monkeypatch) -> None:
    monkeypatch.setattr(worker, "LocalMechDSLBackend", FakeBackend)
    result = worker.handle_payload({"action": "invent"})
    assert result["ok"] is False
    assert result["diagnostic"]["category"] == "ValueError"

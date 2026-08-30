from __future__ import annotations

from typing import Any

import pytest


class FakeCompilerService:
    def __init__(self) -> None:
        emitted = "import taichi as ti\n\n@ti.kernel\ndef residual():\n    pass\n"
        self.compile_result: dict[str, Any] = {
            "ok": True,
            "result_kind": "compile",
            "mode": "mechanics",
            "generated_source": emitted,
            "emitted_source": emitted,
            "element_ir_summary": {
                "element_type": "hex8",
                "dim": 3,
                "n_nodes": 8,
                "n_quadrature_points": 8,
                "formulation": "total_lagrangian",
            },
            "content_hash": "a" * 64,
            "derived_energy_present": False,
        }
        code = "def axpy(a, x, y):\n    return a * x + y\n"
        self.transpile_result: dict[str, Any] = {
            "ok": True,
            "result_kind": "transpile",
            "mode": "algorithm",
            "generated_source": code,
            "code": code,
            "entry_point": "axpy",
            "line_count": 2,
            "valid_python": True,
            "backend": "taichi",
        }
        self.capabilities_result: dict[str, Any] = {
            "ok": True,
            "capabilities": {
                "version": "0.2.0",
                "profiles": ["mvp"],
                "backends": ["taichi"],
                "actions": ["emit", "transpile", "verify"],
            },
            "packages": {"mechdsl-core": "0.2.0", "algo2code": "0.2.0"},
        }
        self.models_result: dict[str, Any] = {
            "ok": True,
            "models": [{"name": "svk", "tier": "mvp"}],
        }
        self.last_compile_request = None
        self.last_transpile_request = None

    async def compile(self, request):
        self.last_compile_request = request
        return self.compile_result

    async def transpile(self, request):
        self.last_transpile_request = request
        return self.transpile_result

    async def capabilities(self):
        return self.capabilities_result

    async def models(self):
        return self.models_result


@pytest.fixture
def fake_service() -> FakeCompilerService:
    return FakeCompilerService()

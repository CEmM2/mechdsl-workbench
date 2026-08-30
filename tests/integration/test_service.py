from __future__ import annotations

import asyncio
import sys
import threading
import time
from pathlib import Path

import pytest

from mechdsl_workbench.compiler.models import CompileRequest, TranspileRequest
from mechdsl_workbench.compiler.service import SubprocessCompilerService
from mechdsl_workbench.config import Settings

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def run(coro):
    return asyncio.run(coro)


def make_service(fixture: str, **settings):
    return SubprocessCompilerService(
        Settings(**settings),
        worker_command=[sys.executable, str(FIXTURES / fixture)],
    )


def test_subprocess_service_compile_success() -> None:
    service = make_service("worker_success.py", compile_timeout_seconds=2.0)
    result = run(service.compile(CompileRequest(problem_source="% mechanics dim 3")))
    assert result["ok"] is True
    assert "@ti.kernel" in result["emitted_source"]


def test_subprocess_service_transpile_success() -> None:
    service = make_service("worker_success.py", compile_timeout_seconds=2.0)
    result = run(service.transpile(TranspileRequest(algorithm_source="% algorithm pcg")))
    assert result["ok"] is True
    assert result["entry_point"] == "pcg"


def test_subprocess_service_timeout_terminates_worker() -> None:
    service = make_service("worker_sleep.py", compile_timeout_seconds=0.05)
    result = run(service.compile(CompileRequest(problem_source="x")))
    assert result["ok"] is False
    assert result["diagnostic"]["category"] == "WorkerTimeout"


def test_subprocess_service_rejects_invalid_worker_json() -> None:
    service = make_service("worker_bad_json.py", compile_timeout_seconds=1.0)
    result = run(service.compile(CompileRequest(problem_source="x")))
    assert result["ok"] is False
    assert result["diagnostic"]["category"] == "WorkerProtocolError"


def test_subprocess_service_rejects_oversized_mechanics_source_before_spawn() -> None:
    service = make_service("worker_success.py", max_source_bytes=4)
    result = run(service.compile(CompileRequest(problem_source="12345")))
    assert result["ok"] is False
    assert result["diagnostic"]["category"] == "SourceTooLarge"


def test_subprocess_service_rejects_oversized_algorithm_source_before_spawn() -> None:
    service = make_service("worker_success.py", max_source_bytes=4)
    result = run(service.transpile(TranspileRequest(algorithm_source="12345")))
    assert result["ok"] is False
    assert result["diagnostic"]["category"] == "SourceTooLarge"


class CountingService(SubprocessCompilerService):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def _invoke(self, payload):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        with self.lock:
            self.active -= 1
        if payload["action"] == "transpile":
            return {
                "ok": True,
                "code": "pass\n",
                "entry_point": "demo",
                "line_count": 1,
                "valid_python": True,
            }
        return {
            "ok": True,
            "emitted_source": "pass\n",
            "element_ir_summary": {},
            "content_hash": "c" * 64,
            "derived_energy_present": False,
        }


def test_compile_and_transpile_share_bounded_worker_slots() -> None:
    service = CountingService(Settings(max_concurrent_compiles=1))

    async def exercise() -> None:
        await asyncio.gather(
            service.compile(CompileRequest(problem_source="x")),
            service.transpile(TranspileRequest(algorithm_source="y")),
        )

    run(exercise())
    assert service.max_active == 1

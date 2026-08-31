"""Compiler service with a hard subprocess timeout and bounded I/O."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from ..config import Settings
from .diagnostics import normalize_exception, worker_diagnostic
from .models import CompileRequest, TranspileRequest, workbench_failure


class CompilerService(Protocol):
    async def compile(self, request: CompileRequest) -> dict[str, Any]: ...

    async def transpile(self, request: TranspileRequest) -> dict[str, Any]: ...

    async def capabilities(self) -> dict[str, Any]: ...

    async def models(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class SubprocessCompilerService:
    """Run every MechDSL operation in an isolated, bounded child process."""

    settings: Settings
    worker_command: Sequence[str] | None = None
    _job_slots: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._job_slots = asyncio.Semaphore(self.settings.max_concurrent_compiles)

    async def compile(self, request: CompileRequest) -> dict[str, Any]:
        size_error = self._validate_text_size("problem_source", request.problem_source)
        if size_error is None and request.energy_source is not None:
            size_error = self._validate_text_size("energy_source", request.energy_source)
        if size_error is not None:
            return workbench_failure(size_error)
        async with self._job_slots:
            return await asyncio.to_thread(
                self._invoke,
                {"action": "compile", "request": request.to_dict()},
            )

    async def transpile(self, request: TranspileRequest) -> dict[str, Any]:
        size_error = self._validate_text_size("algorithm_source", request.algorithm_source)
        if size_error is not None:
            return workbench_failure(size_error)
        async with self._job_slots:
            return await asyncio.to_thread(
                self._invoke,
                {"action": "transpile", "request": request.to_dict()},
            )

    async def capabilities(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._invoke, {"action": "capabilities"})

    async def models(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._invoke, {"action": "models"})

    def _validate_text_size(self, field: str, value: str):
        size = len(value.encode("utf-8"))
        if size <= self.settings.max_source_bytes:
            return None
        return worker_diagnostic(
            category="SourceTooLarge",
            code="WORKBENCH-INPUT-SIZE",
            message=(
                f"{field} is {size} bytes; the configured limit is "
                f"{self.settings.max_source_bytes} bytes"
            ),
        )

    def _invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = list(self.worker_command or _default_worker_command())
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        popen_kwargs: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "env": env,
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":  # pragma: no cover - exercised on Windows CI/deployments
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            process = subprocess.Popen(command, **popen_kwargs)
        except OSError as exc:
            return workbench_failure(normalize_exception(exc))

        action = str(payload.get("action", "compiler"))
        action_label = "Transpilation" if action == "transpile" else "Compilation"
        try:
            stdout, stderr = process.communicate(
                input=encoded,
                timeout=self.settings.compile_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            stdout, stderr = process.communicate()
            details = _decode_and_clip(stderr, 4000)
            return workbench_failure(
                worker_diagnostic(
                    category="WorkerTimeout",
                    code="WORKBENCH-WORKER-TIMEOUT",
                    message=(
                        f"{action_label} exceeded "
                        f"{self.settings.compile_timeout_seconds:g} seconds and was terminated"
                    ),
                    technical_details=details or None,
                )
            )

        if len(stdout) > self.settings.max_worker_output_bytes:
            return workbench_failure(
                worker_diagnostic(
                    category="WorkerOutputTooLarge",
                    code="WORKBENCH-WORKER-OUTPUT",
                    message=(
                        f"Worker returned {len(stdout)} bytes; the configured limit is "
                        f"{self.settings.max_worker_output_bytes} bytes"
                    ),
                )
            )

        try:
            decoded = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            details = _decode_and_clip(stderr, 4000)
            return workbench_failure(
                worker_diagnostic(
                    category="WorkerProtocolError",
                    code="WORKBENCH-WORKER-PROTOCOL",
                    message="Compiler worker did not return valid UTF-8 JSON",
                    technical_details=details or str(exc),
                )
            )

        if not isinstance(decoded, dict):
            return workbench_failure(
                worker_diagnostic(
                    category="WorkerProtocolError",
                    code="WORKBENCH-WORKER-PROTOCOL",
                    message="Compiler worker returned a JSON value that was not an object",
                )
            )

        if process.returncode != 0 and decoded.get("ok") is not False:
            return workbench_failure(
                worker_diagnostic(
                    category="WorkerProcessError",
                    code="WORKBENCH-WORKER-EXIT",
                    message=f"Compiler worker exited with status {process.returncode}",
                    technical_details=_decode_and_clip(stderr, 4000) or None,
                )
            )

        return decoded


def _default_worker_command() -> tuple[str, ...]:
    return (sys.executable, "-m", "mechdsl_workbench.compiler.worker")


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover - exercised on Windows CI/deployments
            process.kill()
    except ProcessLookupError:
        return


def _decode_and_clip(data: bytes, limit: int) -> str:
    text = data.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text.strip()
    return (text[:limit] + "\n… worker stderr clipped …").strip()

"""The only module that talks to the external MechDSL package."""

from __future__ import annotations

import importlib
import importlib.metadata
from typing import Any

from .models import CompileRequest, TranspileRequest


class BackendUnavailable(RuntimeError):
    """Raised when mechdsl-core is not installed or cannot be imported."""


class BackendContractError(RuntimeError):
    """Raised when the public MechDSL integration result has an unexpected shape."""


class LocalMechDSLBackend:
    """Thin adapter over the documented ``mechdsl.integration`` façade.

    The workbench deliberately does not import the standalone ``algo2code`` API.
    Algorithms still travel through ``mechdsl.integration.transpile_algorithm``;
    package metadata is inspected only to provide a useful readiness message.
    """

    def compile(self, request: CompileRequest) -> dict[str, Any]:
        integration = self._integration()
        raw = integration.compile_from_sources(
            problem_source=request.problem_source,
            energy_source=request.energy_source,
            profile=request.profile,
        )
        return _validate_compile_result(raw)

    def transpile(self, request: TranspileRequest) -> dict[str, Any]:
        integration = self._integration()
        raw = integration.transpile_algorithm(
            request.algorithm_source,
            backend=request.backend,
        )
        return _validate_transpile_result(raw)

    def capabilities(self) -> dict[str, Any]:
        raw = self._integration().capabilities()
        if not isinstance(raw, dict):
            raise BackendContractError("mechdsl.integration.capabilities() must return a dict")
        return raw

    def package_versions(self) -> dict[str, str | None]:
        """Report installed distribution versions without importing implementation APIs."""

        return {
            "mechdsl-core": _distribution_version("mechdsl-core"),
            "algo2code": _distribution_version("algo2code"),
        }

    def models(self) -> list[dict[str, Any]]:
        raw = self._integration().model_catalog()
        if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
            raise BackendContractError("mechdsl.integration.model_catalog() must return list[dict]")
        return raw

    @staticmethod
    def _integration() -> Any:
        try:
            return importlib.import_module("mechdsl.integration")
        except ModuleNotFoundError as exc:
            if exc.name == "mechdsl" or (exc.name and exc.name.startswith("mechdsl.")):
                raise BackendUnavailable(
                    "mechdsl-core is not installed in the workbench environment. "
                    "Run scripts/install_pinned_mechdsl.py or install an editable local checkout."
                ) from exc
            raise


def _validate_compile_result(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BackendContractError("compile_from_sources() must return a dict")

    required = {
        "element_ir_summary",
        "emitted_source",
        "content_hash",
        "derived_energy_present",
    }
    missing = sorted(required.difference(raw))
    if missing:
        raise BackendContractError(
            f"compile_from_sources() result is missing keys: {', '.join(missing)}"
        )

    if not isinstance(raw["element_ir_summary"], dict):
        raise BackendContractError("element_ir_summary must be a dict")
    if not isinstance(raw["emitted_source"], str):
        raise BackendContractError("emitted_source must be a string")
    if not isinstance(raw["content_hash"], str):
        raise BackendContractError("content_hash must be a string")
    if not isinstance(raw["derived_energy_present"], bool):
        raise BackendContractError("derived_energy_present must be a bool")

    return raw


def _validate_transpile_result(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BackendContractError("transpile_algorithm() must return a dict")

    required = {"code", "entry_point", "line_count", "valid_python"}
    missing = sorted(required.difference(raw))
    if missing:
        raise BackendContractError(
            f"transpile_algorithm() result is missing keys: {', '.join(missing)}"
        )

    if not isinstance(raw["code"], str):
        raise BackendContractError("transpile result code must be a string")
    if not isinstance(raw["entry_point"], str):
        raise BackendContractError("transpile result entry_point must be a string")
    if not isinstance(raw["line_count"], int) or isinstance(raw["line_count"], bool):
        raise BackendContractError("transpile result line_count must be an int")
    if not isinstance(raw["valid_python"], bool):
        raise BackendContractError("transpile result valid_python must be a bool")

    return raw


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None

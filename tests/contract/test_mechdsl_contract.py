from __future__ import annotations

import importlib
import importlib.metadata
import os

import pytest

from mechdsl_workbench.examples import get_example, list_examples

pytestmark = pytest.mark.contract


def _contract_enabled() -> bool:
    return os.getenv("MECHDSL_CONTRACT_TEST", "").lower() in {"1", "true", "yes"}


@pytest.mark.skipif(not _contract_enabled(), reason="set MECHDSL_CONTRACT_TEST=1")
def test_pinned_mechdsl_public_contract_and_all_examples() -> None:
    integration = importlib.import_module("mechdsl.integration")
    assert importlib.metadata.version("algo2code")

    capabilities = integration.capabilities()
    assert "mvp" in capabilities["profiles"]
    assert "taichi" in capabilities["backends"]
    assert "emit" in capabilities["actions"]
    assert "transpile" in capabilities["actions"]

    for metadata in list_examples():
        example = get_example(metadata["id"])
        if example["mode"] == "mechanics":
            result = integration.compile_from_sources(
                problem_source=example["source"],
                energy_source=example["energy_source"],
                profile="mvp",
            )
            assert isinstance(result["emitted_source"], str)
            assert "@ti.kernel" in result["emitted_source"]
            assert len(result["content_hash"]) == 64
            assert result["element_ir_summary"]["element_type"]
        else:
            result = integration.transpile_algorithm(example["source"], backend="taichi")
            assert isinstance(result["code"], str)
            assert result["code"]
            assert result["entry_point"]
            assert result["line_count"] == len(result["code"].splitlines())
            assert result["valid_python"] is True

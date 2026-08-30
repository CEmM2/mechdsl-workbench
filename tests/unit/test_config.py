from __future__ import annotations

import pytest

from mechdsl_workbench.config import Settings

pytestmark = pytest.mark.unit


def test_settings_from_env_uses_real_defaults(monkeypatch) -> None:
    for name in (
        "MECHDSL_WORKBENCH_HOST",
        "MECHDSL_WORKBENCH_PORT",
        "MECHDSL_WORKBENCH_DEBUG",
        "MECHDSL_WORKBENCH_COMPILE_TIMEOUT",
        "MECHDSL_WORKBENCH_MAX_CONCURRENT_COMPILES",
        "MECHDSL_WORKBENCH_MAX_SOURCE_BYTES",
        "MECHDSL_WORKBENCH_MAX_WORKER_OUTPUT_BYTES",
        "MECHDSL_WORKBENCH_MAX_REQUEST_BYTES",
        "MECHDSL_WORKBENCH_MATHJAX_URL",
        "MECHDSL_WORKBENCH_SUPPORTED_MECHDSL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.compile_timeout_seconds == 30.0
    assert settings.supported_mechdsl == ">=0.2.0,<0.3.0"


def test_settings_from_env_accepts_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MECHDSL_WORKBENCH_PORT", "8123")
    monkeypatch.setenv("MECHDSL_WORKBENCH_DEBUG", "yes")
    monkeypatch.setenv("MECHDSL_WORKBENCH_SUPPORTED_MECHDSL", ">=0.2.0,<0.4")
    settings = Settings.from_env()
    assert settings.port == 8123
    assert settings.debug is True
    assert settings.supported_mechdsl == ">=0.2.0,<0.4"

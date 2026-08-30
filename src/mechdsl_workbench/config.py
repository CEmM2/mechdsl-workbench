"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _env_float(name: str, default: float, *, minimum: float = 0.01) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = float(raw)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the web application and compiler worker."""

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    compile_timeout_seconds: float = 30.0
    max_concurrent_compiles: int = 2
    max_source_bytes: int = 256 * 1024
    max_worker_output_bytes: int = 8 * 1024 * 1024
    max_request_bytes: int = 2 * 1024 * 1024
    mathjax_url: str = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"
    supported_mechdsl: str = ">=0.2.0,<0.3.0"
    static_dir: Path = PACKAGE_ROOT / "static"
    templates_dir: Path = PACKAGE_ROOT / "templates"

    @classmethod
    def from_env(cls) -> Settings:
        defaults = cls()
        return cls(
            host=os.getenv("MECHDSL_WORKBENCH_HOST", defaults.host),
            port=_env_int("MECHDSL_WORKBENCH_PORT", defaults.port, minimum=1),
            debug=_env_bool("MECHDSL_WORKBENCH_DEBUG", defaults.debug),
            compile_timeout_seconds=_env_float(
                "MECHDSL_WORKBENCH_COMPILE_TIMEOUT",
                defaults.compile_timeout_seconds,
            ),
            max_concurrent_compiles=_env_int(
                "MECHDSL_WORKBENCH_MAX_CONCURRENT_COMPILES",
                defaults.max_concurrent_compiles,
            ),
            max_source_bytes=_env_int(
                "MECHDSL_WORKBENCH_MAX_SOURCE_BYTES",
                defaults.max_source_bytes,
            ),
            max_worker_output_bytes=_env_int(
                "MECHDSL_WORKBENCH_MAX_WORKER_OUTPUT_BYTES",
                defaults.max_worker_output_bytes,
            ),
            max_request_bytes=_env_int(
                "MECHDSL_WORKBENCH_MAX_REQUEST_BYTES",
                defaults.max_request_bytes,
            ),
            mathjax_url=os.getenv(
                "MECHDSL_WORKBENCH_MATHJAX_URL",
                defaults.mathjax_url,
            ),
            supported_mechdsl=os.getenv(
                "MECHDSL_WORKBENCH_SUPPORTED_MECHDSL",
                defaults.supported_mechdsl,
            ),
        )

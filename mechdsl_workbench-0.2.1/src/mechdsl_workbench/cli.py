"""Command-line entry point for the workbench server."""

from __future__ import annotations

import argparse

import uvicorn

from .app import create_app
from .config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mechdsl-workbench",
        description="Run the standalone browser workbench for MechDSL.",
    )
    parser.add_argument("--host", help="Bind host; defaults to environment/config")
    parser.add_argument("--port", type=int, help="Bind port; defaults to environment/config")
    parser.add_argument("--reload", action="store_true", help="Enable Uvicorn auto-reload")
    parser.add_argument("--log-level", default="info")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    host = args.host or settings.host
    port = args.port or settings.port

    if args.reload:
        uvicorn.run(
            "mechdsl_workbench.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            log_level=args.log_level,
        )
        return

    uvicorn.run(
        create_app(settings=settings),
        host=host,
        port=port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()

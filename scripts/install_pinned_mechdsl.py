#!/usr/bin/env python3
"""Install the reviewed MechDSL and algo2code revision into the active environment."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

MECHDSL_REV = "f173fd43d56aa13f947f1071d90468a87961c120"  # CEmM2/MechDSL tag v0.2.0
MECHDSL_GIT = "https://github.com/CEmM2/MechDSL.git"
PACKAGES = ("mechdsl-core", "algo2code")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter/virtual environment to install into",
    )
    parser.add_argument(
        "--local",
        type=Path,
        help=(
            "Install editable packages from a local MechDSL checkout. The path may be the "
            "repository root, its packages directory, or packages/mechdsl-core."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.local is not None:
        package_dirs = _local_package_dirs(args.local.expanduser().resolve())
        command = ["uv", "pip", "install", "--python", args.python]
        for package_dir in package_dirs:
            command.extend(["--editable", str(package_dir)])
    else:
        requirements = [
            f"{package} @ git+{MECHDSL_GIT}@{MECHDSL_REV}#subdirectory=packages/{package}"
            for package in PACKAGES
        ]
        command = ["uv", "pip", "install", "--python", args.python, *requirements]

    print(f"Installing mechdsl-core and algo2code into {args.python}")
    subprocess.run(command, check=True)
    return 0


def _local_package_dirs(path: Path) -> tuple[Path, Path]:
    candidates: list[Path] = []

    # Repository root.
    if (path / "packages" / "mechdsl-core" / "pyproject.toml").is_file():
        candidates = [path / "packages" / package for package in PACKAGES]
    # packages/ directory.
    elif (path / "mechdsl-core" / "pyproject.toml").is_file():
        candidates = [path / package for package in PACKAGES]
    # packages/mechdsl-core path retained for v0.1 command compatibility.
    elif path.name == "mechdsl-core" and (path / "pyproject.toml").is_file():
        candidates = [path, path.parent / "algo2code"]

    if not candidates or any(not (candidate / "pyproject.toml").is_file() for candidate in candidates):
        raise SystemExit(
            f"Could not find both packages/mechdsl-core and packages/algo2code from {path}"
        )
    return candidates[0].resolve(), candidates[1].resolve()


if __name__ == "__main__":
    raise SystemExit(main())

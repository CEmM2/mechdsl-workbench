from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "install_pinned_mechdsl",
    ROOT / "scripts" / "install_pinned_mechdsl.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def create_checkout(root: Path) -> None:
    for package in ("mechdsl-core", "algo2code"):
        package_dir = root / "packages" / package
        package_dir.mkdir(parents=True)
        (package_dir / "pyproject.toml").write_text("[project]\nname='x'\n")


def test_local_package_dirs_accept_repo_root(tmp_path) -> None:
    create_checkout(tmp_path)
    core, algo = MODULE._local_package_dirs(tmp_path)
    assert core.name == "mechdsl-core"
    assert algo.name == "algo2code"


def test_local_package_dirs_accept_v01_core_path(tmp_path) -> None:
    create_checkout(tmp_path)
    core, algo = MODULE._local_package_dirs(tmp_path / "packages" / "mechdsl-core")
    assert core.name == "mechdsl-core"
    assert algo.name == "algo2code"


def test_local_package_dirs_rejects_checkout_missing_algo2code(tmp_path) -> None:
    core = tmp_path / "packages" / "mechdsl-core"
    core.mkdir(parents=True)
    (core / "pyproject.toml").write_text("[project]\nname='x'\n")
    with pytest.raises(SystemExit, match="both packages"):
        MODULE._local_package_dirs(tmp_path)


def test_pinned_install_command_contains_both_workspace_packages(monkeypatch) -> None:
    captured = {}

    def fake_run(command, check):
        captured["command"] = command
        captured["check"] = check

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    assert MODULE.main(["--python", "/tmp/python"]) == 0
    command = captured["command"]
    assert captured["check"] is True
    assert any(item.startswith("mechdsl-core @ git+") for item in command)
    assert any(item.startswith("algo2code @ git+") for item in command)

#!/usr/bin/env python3
"""Fail if application source bypasses the public MechDSL integration façade."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "mechdsl_workbench"
ALLOWED_MECHDSL = "mechdsl.integration"


def main() -> int:
    violations: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    violation = _module_violation(alias.name)
                    if violation:
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: import {alias.name} ({violation})"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                violation = _module_violation(module)
                if violation:
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: from {module} ({violation})"
                    )
            elif isinstance(node, ast.Call) and _is_import_module_call(node):
                value = node.args[0].value
                violation = _module_violation(value)
                if violation:
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: import_module({value!r}) "
                        f"({violation})"
                    )

    if violations:
        print("Public integration boundary violations:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    print(
        "MechDSL boundary check passed: application code uses only "
        "mechdsl.integration and never imports algo2code directly."
    )
    return 0


def _module_violation(module: str) -> str | None:
    if module.startswith("mechdsl") and module != ALLOWED_MECHDSL:
        return "private MechDSL surface"
    if module == "algo2code" or module.startswith("algo2code."):
        return "algo2code must be reached through mechdsl.integration"
    return None


def _is_import_module_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "importlib"
        and node.func.attr == "import_module"
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    )


if __name__ == "__main__":
    raise SystemExit(main())

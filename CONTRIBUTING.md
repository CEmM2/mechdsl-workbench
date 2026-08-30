# Contributing

The workbench consumes public MechDSL integration APIs. It is not a second
compiler frontend and it is not an `algo2code` fork.

```text
mechdsl-workbench -> mechdsl.integration -> mechdsl-core / algo2code
MechDSL           -X-> mechdsl-workbench
```

## Development setup

```bash
uv sync --group dev
uv run --no-sync pytest -m "not contract"
uv run --no-sync ruff check .
uv run --no-sync python scripts/check_public_mechdsl_boundary.py
```

Install both external packages when running contract tests:

```bash
uv run --no-sync python scripts/install_pinned_mechdsl.py --local ../MechDSL
MECHDSL_CONTRACT_TEST=1 uv run --no-sync pytest -m contract
```

## Rules

1. Import only `mechdsl.integration`. Do not import private MechDSL modules.
2. Do not import `algo2code` directly. Algorithms must use the public MechDSL
   integration façade just like mechanics compilation.
3. Never execute generated Taichi/Python source in the server or worker.
4. Do not accept server-side file paths from HTTP requests.
5. Preserve structured diagnostics. Do not scrape messages to invent source
   locations or semantics.
6. Add a contract test before depending on a new integration result key.
7. Keep bundled examples versioned with the workbench and compile/transpile all
   of them in the authenticated contract workflow.

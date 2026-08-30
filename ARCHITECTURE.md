# Architecture

## Dependency boundary

```text
Browser
  |
  v
Starlette application
  |
  v
Compiler service
  |
  +-- short-lived subprocess
        |
        v
    mechdsl.integration
        |
        +-- compile_from_sources(...)  -> mechdsl-core
        |
        +-- transpile_algorithm(...)   -> algo2code
```

Only `src/mechdsl_workbench/compiler/backend.py` knows how to load MechDSL,
and it loads only `mechdsl.integration`. It does not import `algo2code`; the
algorithm dependency remains behind the same public façade. The HTTP layer
operates on local request/result dataclasses and JSON dictionaries.

`scripts/check_public_mechdsl_boundary.py` statically rejects both private
MechDSL imports and direct `algo2code` imports from application source.

## Dual-mode result model

Mechanics and algorithms retain their domain-specific public fields:

```text
mechanics: emitted_source, element_ir_summary, content_hash, ...
algorithm: code, entry_point, line_count, valid_python
```

The worker adds `result_kind`, `mode`, and `generated_source` so the shared UI
can display and download either output without erasing the upstream contract.

## Web stack

The external application uses Starlette, Jinja2, and dependency-free browser
JavaScript. It does not reuse MechDSL's workspace-level UI dependencies because
the compiler and workbench have separate installation and release cycles.

The browser preview intentionally does not implement either compiler grammar.
It safely extracts familiar directive comments for orientation; actual meaning
comes only from the public integration response.

## Why a subprocess per action

Symbolic compilation and algorithm parsing can consume CPU or trigger an
unexpected dependency failure. Every compile or transpile action therefore
runs in a short-lived child process with:

- one JSON request and response;
- a hard timeout;
- bounded source and response sizes;
- a shared application semaphore limiting concurrent workers;
- process-group termination on timeout.

Generated code is never imported or executed. This is useful failure isolation,
not a hostile-input sandbox. Public deployment still requires OS/container
resource controls and authentication.

## Readiness

`/readyz` reports ready only when all v0.2 product surfaces are available:

- compatible MechDSL version;
- `mvp` profile;
- Taichi backend;
- `emit` action;
- `transpile` action;
- installed `algo2code` distribution.

The status object distinguishes `mechanics_ready` and `algorithm_ready`, so a
missing `algo2code` installation is reported as partial readiness rather than
masquerading as a generic compiler failure.

## HTTP API

- `GET /` — dual-mode workbench UI
- `POST /api/preview` — safe mode-aware source preview
- `POST /api/compile` — compile mechanics problem and optional energy source
- `POST /api/transpile` — transpile an `algpseudocode` source
- `GET /api/examples` — example metadata, optionally filtered by mode
- `GET /api/examples/{id}` — example source
- `GET /api/capabilities` — MechDSL manifest and installed package versions
- `GET /api/models` — MechDSL model catalogue
- `GET /healthz` — application liveness
- `GET /readyz` — complete toolchain readiness

## Non-goals for v0.2

- executing emitted solver or algorithm code;
- mesh upload or result visualization;
- exact `pdflatex` rendering;
- AST or private IR inspection;
- NumPy/C/PETSc backend selection before the public integration façade exposes
  those as supported contracts;
- user accounts or server-side project storage.

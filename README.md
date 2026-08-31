# MechDSL Workbench

A standalone browser application for two public MechDSL workflows:

1. compile mechanics LaTeX through `mechdsl.integration.compile_from_sources()`;
2. transpile LaTeX `algpseudocode` through
   `mechdsl.integration.transpile_algorithm()` and the external `algo2code`
   package.

```text
┌─────────────────────────────────────────────────────────────────┐
│ Mechanics | Algorithm        Example ▾            Compile/Run  │
├─────────────────────────────────────────────────────────────────┤
│ LaTeX source                                                    │
│                                                                 │
│ % mechanics ...        or        % algorithm pcg               │
│                                  \begin{algorithmic} ...        │
├─────────────────────────────────────────────────────────────────┤
│ Preview | Generated Taichi | Translation View | Diagnostics    │
└─────────────────────────────────────────────────────────────────┘
```

The workbench is external to the MechDSL monorepo. Its dependency direction is
strictly one-way:

```text
mechdsl-workbench -> mechdsl.integration -> mechdsl-core / algo2code
MechDSL           -X-> mechdsl-workbench
```

Application code never imports `algo2code` directly and never reaches into
MechDSL parser, IR, lowering, symbolic, or code-generation internals. The one
public integration boundary is checked in CI.

## Included in v0.2

### Mechanics mode

- line-numbered LaTeX editor;
- optional separate constitutive-energy source;
- safe MathJax-oriented preview and `% mechanics` directive cards;
- generated Taichi source;
- public ElementIR summary, semantic hash, and derived-energy status;
- SVK Hex8, equation-bearing Hex8, and Tet4 examples.

### Algorithm mode

- LaTeX `algorithmic` editor;
- `% algorithm`, `% backend`, `% args`, and `% type` contract preview;
- transpilation through `mechdsl.integration.transpile_algorithm()`;
- generated Taichi/Python source;
- entry-point name, line count, backend, and Python-validity result;
- canonical J2 radial-return and PCG examples.

### Shared behavior

- explicit action button and `Ctrl+Enter` / `Cmd+Enter` shortcut;
- copy and download actions for source and generated `.py` files;
- browser-local drafts maintained separately for both modes;
- short-lived worker subprocesses with a hard timeout;
- shared concurrency, request-size, source-size, and worker-output limits;
- structured diagnostics;
- liveness and full-toolchain readiness endpoints;
- no execution of emitted source.

The preview is presentational. The Translation View is populated only from the
public integration result and is the authoritative account of what the compiler
or transpiler returned.

## Requirements

- Python 3.12;
- [`uv`](https://docs.astral.sh/uv/);
- network access to the public [`CEmM2/MechDSL`](https://github.com/CEmM2/MechDSL)
  repository, or a local MechDSL checkout containing both workspace packages:
  - `packages/mechdsl-core`;
  - `packages/algo2code`.

The installer pins both packages to MechDSL `v0.2.0`:

```text
f173fd43d56aa13f947f1071d90468a87961c120
```

## Install from PyPI

```bash
pip install "mechdsl-workbench[mechdsl]"   # workbench + the MechDSL engine, one command
pip install mechdsl-workbench              # workbench alone (bring your own mechdsl-core)
```

The `[mechdsl]` extra pulls `mechdsl-core[verify]` and `algo2code` from PyPI —
the full engine, including Taichi (expect a large download).

## Install with the pinned Git dependencies

```bash
git clone https://github.com/CEmM2/mechdsl-workbench.git
cd mechdsl-workbench

uv sync --group dev
uv run --no-sync python scripts/install_pinned_mechdsl.py
uv run --no-sync mechdsl-workbench
```

Open `http://127.0.0.1:8000`.

The installer clones over https and installs both pinned subpackages after the
normal workbench sync. A later exact `uv sync` may remove externally installed
packages; rerun the installer afterward or deliberately use an inexact sync.

## Install against a local MechDSL checkout

With sibling repositories:

```text
workspace/
├── MechDSL/
└── mechdsl-workbench/
```

run:

```bash
cd workspace/mechdsl-workbench
uv sync --group dev
uv run --no-sync python scripts/install_pinned_mechdsl.py --local ../MechDSL
uv run --no-sync mechdsl-workbench
```

The v0.1 form remains accepted:

```bash
uv run --no-sync python scripts/install_pinned_mechdsl.py \
  --local ../MechDSL/packages/mechdsl-core
```

The installer resolves the sibling `algo2code` package automatically and fails
if either package is absent.

## Run options

```bash
uv run --no-sync mechdsl-workbench --host 127.0.0.1 --port 8000
uv run --no-sync mechdsl-workbench --reload
```

Environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `MECHDSL_WORKBENCH_HOST` | `127.0.0.1` | Bind address |
| `MECHDSL_WORKBENCH_PORT` | `8000` | Bind port |
| `MECHDSL_WORKBENCH_DEBUG` | `0` | Starlette debug mode |
| `MECHDSL_WORKBENCH_COMPILE_TIMEOUT` | `30` | Hard timeout for either translation action |
| `MECHDSL_WORKBENCH_MAX_CONCURRENT_COMPILES` | `2` | Shared mechanics/algorithm worker concurrency |
| `MECHDSL_WORKBENCH_MAX_SOURCE_BYTES` | `262144` | Per-source UTF-8 byte limit |
| `MECHDSL_WORKBENCH_MAX_WORKER_OUTPUT_BYTES` | `8388608` | Maximum worker JSON output |
| `MECHDSL_WORKBENCH_MAX_REQUEST_BYTES` | `2097152` | HTTP request body limit |
| `MECHDSL_WORKBENCH_MATHJAX_URL` | jsDelivr MathJax 3 | Browser math renderer; empty disables it |
| `MECHDSL_WORKBENCH_SUPPORTED_MECHDSL` | `>=0.2.0,<0.3.0` | Accepted public integration version range |

The application does not automatically read `.env`; `.env.example` is a
reference for shell, container, or service configuration.

## Docker

The Docker build installs both pinned workspace packages over https:

```bash
docker build -t mechdsl-workbench .
docker run --rm -p 8000:8000 mechdsl-workbench
```

Or:

```bash
docker compose build
docker compose up
```

## Worker isolation

Both modes use the same subprocess protocol:

```text
HTTP request
    |
    v
bounded JSON payload
    |
    v
python -m mechdsl_workbench.compiler.worker
    |
    +-- mechanics -> mechdsl.integration.compile_from_sources(...)
    |
    +-- algorithm -> mechdsl.integration.transpile_algorithm(...)
```

The server terminates the process on timeout. Dependency stdout is redirected
to worker stderr so the JSON protocol remains parseable. Generated source is
returned as text and is never imported or executed.

This is process isolation, not a hostile-input sandbox. A public deployment
still needs OS/container CPU, memory, filesystem, network, authentication, and
rate limits.

## HTTP API

### Compile mechanics

```bash
curl -s http://127.0.0.1:8000/api/compile \
  -H 'content-type: application/json' \
  -d '{
    "problem_source": "% mechanics dim 3\n% mechanics cell hex8\n% mechanics formulation total_lagrangian\n% mechanics material svk --E 200e3 --nu 0.3",
    "energy_source": null,
    "profile": "mvp"
  }'
```

The successful response retains the specific MechDSL fields and adds generic
workbench fields used by the shared UI:

```json
{
  "ok": true,
  "result_kind": "compile",
  "mode": "mechanics",
  "generated_source": "...",
  "emitted_source": "...",
  "element_ir_summary": {
    "element_type": "hex8",
    "dim": 3,
    "n_nodes": 8,
    "n_quadrature_points": 8,
    "formulation": "total_lagrangian"
  },
  "content_hash": "...",
  "derived_energy_present": false
}
```

### Transpile an algorithm

```bash
curl -s http://127.0.0.1:8000/api/transpile \
  -H 'content-type: application/json' \
  -d '{
    "algorithm_source": "% algorithm demo\n% backend taichi\n% args x:scalar\n\\begin{algorithmic}\n\\Return $x$\n\\end{algorithmic}",
    "backend": "taichi"
  }'
```

Successful response:

```json
{
  "ok": true,
  "result_kind": "transpile",
  "mode": "algorithm",
  "generated_source": "...",
  "code": "...",
  "entry_point": "demo",
  "line_count": 12,
  "valid_python": true,
  "backend": "taichi"
}
```

Compiler/transpiler failures use HTTP 200 with `ok: false`, because the HTTP
operation succeeded and the structured translation result is the response.
Malformed JSON, missing fields, and oversized HTTP requests use 4xx responses.

### Other endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/preview` | Safe mode-aware presentational preview |
| `GET /api/examples?mode=algorithm` | Filtered example metadata |
| `GET /api/examples/{id}` | Example source |
| `GET /api/capabilities` | MechDSL capabilities plus installed package versions |
| `GET /api/models` | Public MechDSL model catalogue |
| `GET /healthz` | Web-process liveness |
| `GET /readyz` | Readiness of both mechanics and algorithm toolchains |

## Tests

The ordinary suite needs neither private package. It injects a fake public
service and separately exercises the actual subprocess protocol:

```bash
uv sync --group dev
uv run --no-sync ruff check .
uv run --no-sync python scripts/check_public_mechdsl_boundary.py
uv run --no-sync pytest -m "not contract"
```

Run the real pinned contract after installing both packages:

```bash
uv run --no-sync python scripts/install_pinned_mechdsl.py
MECHDSL_CONTRACT_TEST=1 uv run --no-sync pytest -m contract
```

The contract suite compiles every mechanics example and transpiles every
algorithm example through `mechdsl.integration`.

## Updating the MechDSL pin

1. Change `MECHDSL_REV` in `scripts/install_pinned_mechdsl.py`.
2. Install both pinned packages.
3. Run the non-contract and contract suites.
4. Review generated-source changes for all bundled examples.
5. Commit the pin and any deliberate adapter changes together.

Do not respond to an integration API change by importing private MechDSL or
direct `algo2code` modules. That transforms an obvious incompatibility into a
more imaginative maintenance problem.

## Project layout

```text
src/mechdsl_workbench/
├── app.py                  # HTTP routes and application factory
├── compiler/
│   ├── backend.py          # sole mechdsl.integration adapter
│   ├── diagnostics.py      # stable UI diagnostics
│   ├── models.py           # compile/transpile request and result models
│   ├── service.py          # subprocess management and limits
│   └── worker.py           # JSON-over-stdio worker
├── examples/               # mechanics and algorithm sources
├── services/preview.py     # safe mode-aware preview
├── static/                 # dependency-free browser UI
└── templates/index.html    # two-pane dual-mode workbench
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for boundaries and non-goals.

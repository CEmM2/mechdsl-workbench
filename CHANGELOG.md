# Changelog

## [0.2.1] - 2026-08-31

### Changed

- Version bump in lock-step with the MechDSL workspace packages (first PyPI-era release).
- Prepared (commented, activation-gated) `[mechdsl]` extra: once `mechdsl-core`/`algo2code` 0.2.1 are on PyPI, `pip install "mechdsl-workbench[mechdsl]"` installs the workbench together with the engine.


## 0.2.0 - 2026-08-18

- Added a top-level Mechanics/Algorithm mode selector.
- Added `algo2code` support through
  `mechdsl.integration.transpile_algorithm()` without direct package imports.
- Added isolated `/api/transpile` and worker `transpile` actions.
- Added entry-point, line-count, backend, and Python-validity presentation.
- Added safe previews for `% algorithm`, `% backend`, `% args`, and `% type`
  directives and `algorithmic` bodies.
- Added canonical J2 radial-return and PCG examples.
- Updated the pinned installer to install both `mechdsl-core` and `algo2code`
  from the same reviewed MechDSL revision.
- Added partial/full readiness reporting for the two toolchains.
- Added generic shared output keys while retaining domain-specific integration
  result fields.
- Expanded unit, HTTP, subprocess, installer, boundary, and opt-in real-contract
  tests.

## 0.1.0 - 2026-08-18

- Added the standalone two-pane LaTeX-to-Taichi mechanics workbench.
- Added safe directive/document preview and optional energy-source editing.
- Added isolated compilation through the public `mechdsl.integration` façade.
- Added generated-code, compiler-summary, and structured-diagnostics views.
- Added curated examples, local draft persistence, copy/download actions, and
  readiness/liveness endpoints.

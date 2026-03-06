# Repository Evolution Plan

This project is intentionally split into two repositories so core simulation and web integration can evolve in parallel.

## Repository Roles

### 1) Core Engine Repo

- Repository: `PHAERO_2_ESBO_v2`
- Responsibility:
  - IDA ICE automation (`phase0/`, `util.py`)
  - Zone creation, simulation orchestration, result extraction
  - Stable CLI workflow
- Rule:
  - No web-specific API/server logic here

### 2) Web Integration Repo

- Repository: `PHAERO_2_ESBO_v2_webapp`
- Responsibility:
  - HTTP API (`webapi/`)
  - Job queue/runner behavior for web requests
  - Packaging and returning outputs for frontend consumption
- Rule:
  - Avoid forking core logic; consume it as a dependency

## Original Plan and Why This Split

Original flow:
1. Generate input JSON (from app).
2. Combine input with CSV metadata.
3. Generate LISP script.
4. Run IDA ICE simulations.
5. Export PRN/PNG/summary JSON.
6. Postprocess and aggregate by `zone_type`.

This split preserves that flow while allowing:
- Core team to improve simulation reliability/performance.
- Integration team to improve API/web UX independently.

## Integration Contract

The web repository depends on the core repository through a **versioned contract**:

- Input contract: zone JSON schema (+ required CSV semantics).
- Output contract: summary reports, time series, images, and combined aggregates.
- Runtime contract: supported flags and reader modes.

Document and version any breaking change to these contracts.

## Recommended Dependency Strategy

Prefer pinning core repo by Git tag in web repo:

```text
git+https://github.com/<org>/PHAERO_2_ESBO_v2.git@v0.1.0
```

Alternative: Git submodule.

Preferred for this project: version pinning by tag, because upgrades are explicit and easy to roll back.

## Versioning Policy

Use semantic versioning for core repo releases:

- `MAJOR`: breaking contract change
- `MINOR`: new backward-compatible feature
- `PATCH`: bugfix, no contract change

Web repo should always pin an explicit core version and keep a simple compatibility table.

## Compatibility Matrix (Template)

```text
Web Repo Version    Core Repo Version    Status
v0.1.x              v0.1.x               supported
v0.2.x              v0.2.x               supported
```

## Branching and Release Flow

### Core Repo

- `main`: stable working checkpoint
- `feature/*`: development
- release tags: `vX.Y.Z`

### Web Repo

- `main`: deployable API integration
- `feature/*`: API/UI integration features
- Dependency bump PRs: one PR per core version upgrade

## Parallel Development Workflow

1. Core team ships `vX.Y.Z` tag in core repo.
2. Web team opens a dependency bump PR in web repo.
3. Run integration tests against real/representative IDA scenarios.
4. Merge if passing; rollback by pinning previous tag if needed.

## Testing Strategy

### Core Tests

- Unit tests around parsing/geometry/lisp generation.
- Integration tests for stage flow and file outputs.

### Web Tests

- API contract tests (`POST /jobs`, status polling, results payload).
- End-to-end smoke test using one known JSON input.
- Non-regression tests for result bundle structure.

## Risk Controls

- Keep one job worker by default (`max_workers=1`) unless IDA license/session capacity is proven.
- Add strict JSON schema validation at API boundary.
- Add auth/rate limiting before external exposure.
- Keep full run manifests and logs for traceability.

## 90-Day Roadmap (Suggested)

1. Stabilize contracts:
   - Freeze v1 input/output schemas
   - Add schema docs and validation
2. Improve reliability:
   - Better retry/error classification
   - Health checks and timeout policies
3. Improve operability:
   - Structured logs
   - Dashboard-ready job metadata
4. Scale cautiously:
   - Controlled increase of workers
   - License-aware scheduling

## Documentation Map

- `README.md`: quick start and mode overview.
- `PIPELINE_INPUT_OUTPUT.md`: technical dataflow and artifacts.
- `WEBAPP_BRIDGE_LOGIC.md`: API bridge runtime logic.
- `REPO_EVOLUTION_PLAN.md` (this file): governance and evolution strategy.

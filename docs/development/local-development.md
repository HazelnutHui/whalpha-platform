# Local Development

## Current Status

The workstation application includes:

- FastAPI Health plus default-disabled private EOD and market-overview routes under `apps/api`
- canonical Parquet read/query services, close-to-close analytics, Dashboard Overview, and snapshot export
- React/Vite Dashboard V1.1 under `apps/web` with API, demo, and snapshot modes
- local scripts `scripts/dev/run-api.sh` and `scripts/dev/run-web.sh`

Backend tests, the Health API localhost check, frontend regression/build, Vite local server, and Vite-to-FastAPI proxy have been verified on `dell5820`. Node.js 24 LTS and npm are installed; see [Node Toolchain Provisioning](../operations/node-toolchain-provisioning.md).

## Prerequisites

- Python 3.12
- Python `venv` support
- Node.js 24 LTS and npm for frontend development
- No sudo is required for project-local setup

## Repository Layout

```text
apps/api    FastAPI backend scaffold
apps/web    React/Vite frontend scaffold
scripts/dev local development launch scripts
docs        project documentation
```

## Backend Setup

```bash
cd /home/hui/projects/trading-intelligence-platform
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e "./apps/api[dev]"
```

This creates a project-local virtualenv. Do not install project dependencies into the system Python environment.

## Frontend Setup

```bash
cd /home/hui/projects/trading-intelligence-platform/apps/web
npm install
```

This creates `node_modules` locally under `apps/web` and maintains `package-lock.json`. Do not use global npm installs for project dependencies.

## Start Backend

```bash
cd /home/hui/projects/trading-intelligence-platform
scripts/dev/run-api.sh
```

The script starts Uvicorn on `127.0.0.1:8000` and does not bind to public interfaces.

The default app exposes only Health. For an explicitly authorized local/private canonical-data session, set `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true` before starting the API. That flag is not authentication or public deployment approval.

For the Market Regime local preview, first build a canonical bundle from the
three explicit completed audits:

```bash
scripts/admin/build-market-regime-preview.sh \
  --as-of-session 2026-08-21 \
  --phase1a-audit /tmp/<explicit-phase1a-audit> \
  --phase1b-audit /tmp/<explicit-phase1b-audit> \
  --phase2-audit /tmp/<explicit-phase2-audit> \
  --output-dir /tmp/<new-empty-preview-directory>
```

Then start the API with both explicit preview settings:

```bash
TIP_ENABLE_MARKET_REGIME_PREVIEW_ROUTES=true \
TIP_MARKET_REGIME_PREVIEW_BUNDLE=/tmp/<explicit-completed-bundle> \
PYTHONPATH=apps/api/src .venv/bin/uvicorn tip_api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:5173/?view=regime`. The bundle and routes are local
preview infrastructure only; neither setting authorizes Production use.

## Start Frontend

```bash
cd /home/hui/projects/trading-intelligence-platform
scripts/dev/run-web.sh
```

The Vite development server proxies `/api` to `http://127.0.0.1:8000`.

## Health Check

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok","service":"trading-intelligence-api","version":"0.1.0"}
```

## Test Backend

```bash
cd /home/hui/projects/trading-intelligence-platform
scripts/dev/run-project-python.sh -m pytest apps/api/tests
```

The project runner always places the current checkout or Codex worktree's
`apps/api/src` first on `PYTHONPATH`. A linked worktree may reuse the main Dell
checkout's virtual environment without silently importing the main checkout's
source code. `TIP_PYTHON_BIN` may select another compatible interpreter.

## Build Frontend

```bash
cd /home/hui/projects/trading-intelligence-platform/apps/web
npm run build
```

This build has been verified after `npm install` succeeded.

## Development Boundaries

- Provider configuration exists outside Git but is not loaded by ordinary tests or the default Health-only app.
- All ordinary tests use fixtures or injected fake transports; do not run live SEC or Massive entrypoints as part of local verification.
- Canonical production data remains under `/data/trading-intelligence-platform`; tests write only to temporary roots.
- No database exists.
- Snapshot/bundle/deployment tooling exists, but no OCI change is part of local development setup.
- Do not store secrets in Git.
- Do not bind local development servers to `0.0.0.0`.

## Troubleshooting

- If `scripts/dev/run-api.sh` reports a missing virtualenv, run the backend setup commands.
- If `scripts/dev/run-web.sh` reports missing `node` or `npm`, complete the prepared Node.js 24 provisioning procedure before running frontend development.
- If `scripts/dev/run-web.sh` reports missing `node_modules`, run `npm install` in `apps/web`.
- If the frontend shows API unavailable, start the backend and confirm the health check succeeds.

## Current Limitations

- Private routes are default-disabled and have no formal multi-user API authentication.
- The bounded historical EOD/Identity acquisition is complete. The guarded
  daily chain is agent-runnable and has a read-only wake timer; unattended
  write-capable execution is not installed.
- There is no database, corporate-action reconciliation, point-in-time sector taxonomy, or market-cap dataset.
- Theme/relationship analytics, Options ingestion, and the full Event Engine remain deferred.
- The production deployment design is static snapshot based; no production FastAPI service is deployed.

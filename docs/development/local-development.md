# Local Development

## Current Status

The minimal application scaffold exists:

- Backend scaffold: `apps/api`
- Frontend scaffold: `apps/web`
- Versioned Health API contract: `GET /api/v1/health`
- Local development scripts: `scripts/dev/run-api.sh` and `scripts/dev/run-web.sh`

Backend dependency installation, backend tests, and the Health API localhost check were verified during scaffold creation. Frontend dependency installation and build were not verified because Node.js and npm were unavailable on the workstation at that time.

## Prerequisites

- Python 3.12
- Python `venv` support
- Node.js and npm for frontend development
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

This creates `node_modules` locally under `apps/web`. Do not use global npm installs for project dependencies.

## Start Backend

```bash
cd /home/hui/projects/trading-intelligence-platform
scripts/dev/run-api.sh
```

The script starts Uvicorn on `127.0.0.1:8000` and does not bind to public interfaces.

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
.venv/bin/python -m pytest apps/api/tests
```

## Build Frontend

```bash
cd /home/hui/projects/trading-intelligence-platform/apps/web
npm run build
```

Run this only after `npm install` succeeds.

## Development Boundaries

- No real market data provider is configured.
- No Massive or IBKR credentials are configured.
- No database exists.
- No production deployment pipeline exists.
- No OCI change is part of local development setup.
- Do not store secrets in Git.
- Do not bind local development servers to `0.0.0.0`.

## Troubleshooting

- If `scripts/dev/run-api.sh` reports a missing virtualenv, run the backend setup commands.
- If `scripts/dev/run-web.sh` reports missing `node` or `npm`, install the frontend toolchain outside this repository before running frontend development.
- If `scripts/dev/run-web.sh` reports missing `node_modules`, run `npm install` in `apps/web`.
- If the frontend shows API unavailable, start the backend and confirm the health check succeeds.

## Current Limitations

- The frontend is a development status page, not Dashboard V1.
- The backend exposes only the versioned Health API.
- The provider boundary is documented but not implemented.
- No market data is loaded.
- No analytics pipeline is implemented.
- No production deployment has been created.

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="${REPO_ROOT}/apps/api/src${PYTHONPATH:+:${PYTHONPATH}}"
exec .venv/bin/python -m tip_api.services.etf_relationship_cli "$@"

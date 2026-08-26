#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${repo_root}/apps/api/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${repo_root}/.venv/bin/python" -m tip_api.services.market_intelligence_publication_cli "$@"

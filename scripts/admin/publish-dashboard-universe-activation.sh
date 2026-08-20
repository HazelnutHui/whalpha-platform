#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root/apps/api"
exec ../../.venv/bin/python -m tip_api.services.dashboard_universe_activation_cli "$@"

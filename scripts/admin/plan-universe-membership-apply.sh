#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$repo_root/.venv/bin/python" -m tip_api.services.universe_membership_apply_plan_cli "$@"

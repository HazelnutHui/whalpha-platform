#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$repo_root/.venv/bin/python" \
  -m tip_api.services.historical_corporate_action_source_publication_plan_cli "$@"

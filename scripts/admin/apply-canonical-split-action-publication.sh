#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$repo_root/.venv/bin/python" \
  -m tip_api.services.canonical_split_action_publication_apply_cli "$@"

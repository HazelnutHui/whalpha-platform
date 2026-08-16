#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ "$(hostname)" != "dell5820" || "$(id -un)" != "hui" ]]; then
  printf 'error=command must run as hui on dell5820\n' >&2
  exit 1
fi

exec .venv/bin/python -m tip_api.providers.sec.live_ingestion "$@"

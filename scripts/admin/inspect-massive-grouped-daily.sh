#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  printf 'usage: inspect-massive-grouped-daily.sh --session-date YYYY-MM-DD
'
  printf 'Runs one read-only Massive Grouped Daily inspection request and prints safe aggregate counts.
'
  exit 0
fi

if [[ "$#" -ne 2 || "${1:-}" != "--session-date" ]]; then
  printf 'error=usage
' >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
cd "$repo_root"

exec .venv/bin/python -m tip_api.providers.massive.grouped_daily_inspection --session-date "$2"

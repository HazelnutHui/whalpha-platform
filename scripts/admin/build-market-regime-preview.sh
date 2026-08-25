#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

if [[ ! -x "${repo_root}/.venv/bin/python" ]]; then
  echo "project virtualenv is unavailable" >&2
  exit 1
fi

export PYTHONPATH="${repo_root}/apps/api/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${repo_root}/.venv/bin/python" -m tip_api.services.market_regime_preview_cli "$@"

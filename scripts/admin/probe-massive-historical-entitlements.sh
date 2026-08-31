#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
export PYTHONPATH="${repo_root}/apps/api/src"
cd "${repo_root}"
exec .venv/bin/python -m tip_api.providers.massive.historical_entitlement_probe_cli "$@"

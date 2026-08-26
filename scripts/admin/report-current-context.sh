#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
cd "${repo_root}"
export PYTHONDONTWRITEBYTECODE=1
python_bin="${repo_root}/.venv/bin/python"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="/home/hui/projects/trading-intelligence-platform/.venv/bin/python"
fi
if [[ ! -x "${python_bin}" ]]; then
  echo "Project Python environment is unavailable" >&2
  exit 1
fi
export PYTHONPATH="${repo_root}/apps/api/src"
exec "${python_bin}" -m tip_api.services.current_context_report "$@"

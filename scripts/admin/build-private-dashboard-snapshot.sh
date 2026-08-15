#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
venv_python="${repo_root}/.venv/bin/python"

if [[ ! -x "${venv_python}" ]]; then
  echo "Project virtualenv was not found." >&2
  exit 1
fi

cd "${repo_root}"
exec "${venv_python}" -m tip_api.services.private_dashboard_snapshot_cli "$@"

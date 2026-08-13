#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
venv_python="${repo_root}/.venv/bin/python"

if [[ ! -x "${venv_python}" ]]; then
  cat >&2 <<MSG
Project virtualenv was not found.

Initialize backend dependencies with:
  cd ${repo_root}
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e "./apps/api[dev]"
MSG
  exit 1
fi

cd "${repo_root}"
exec "${venv_python}" -m uvicorn tip_api.main:app   --app-dir "${repo_root}/apps/api/src"   --host 127.0.0.1   --port 8000   --reload

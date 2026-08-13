#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
web_dir="${repo_root}/apps/web"

if ! command -v node >/dev/null 2>&1; then
  echo "node was not found. Install Node.js for local frontend development before running this script." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found. Install npm for local frontend development before running this script." >&2
  exit 1
fi

if [[ ! -d "${web_dir}/node_modules" ]]; then
  cat >&2 <<MSG
Frontend dependencies were not found.

Initialize frontend dependencies with:
  cd ${web_dir}
  npm install
MSG
  exit 1
fi

cd "${web_dir}"
exec npm run dev -- --host 127.0.0.1

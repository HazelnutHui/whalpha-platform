#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)

python_bin=${TIP_PYTHON_BIN:-"${repo_root}/.venv/bin/python"}
if [[ ! -x "${python_bin}" ]]; then
  git_common_dir=$(git -C "${repo_root}" rev-parse --path-format=absolute --git-common-dir)
  shared_checkout_root=$(dirname -- "${git_common_dir}")
  python_bin="${shared_checkout_root}/.venv/bin/python"
fi
if [[ ! -x "${python_bin}" ]]; then
  echo "Project Python environment is unavailable" >&2
  exit 1
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${repo_root}/apps/api/src${PYTHONPATH:+:${PYTHONPATH}}"
cd "${repo_root}"
exec "${python_bin}" "$@"

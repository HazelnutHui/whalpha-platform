#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'usage: %s\n' "$(basename "$0")"
  printf 'Runs one read-only Massive Stocks reference request using the protected credential file.\n'
}

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi
if [[ $# -eq 1 ]]; then
  if [[ "$1" == "--help" ]]; then
    usage
    exit 0
  fi
  usage >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
python_bin="${repo_root}/.venv/bin/python"

if [[ ! -x "${python_bin}" ]]; then
  printf 'error=missing-project-virtualenv\n' >&2
  exit 1
fi

cd "${repo_root}"
exec "${python_bin}" -m tip_api.providers.massive.smoke_test

#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)

exec "${repo_root}/scripts/dev/run-project-python.sh" \
  -m tip_api.services.strong_leader_pullback_terminal_reference_sec_source_cli "$@"

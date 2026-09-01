#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)

exec "${repo_root}/scripts/dev/run-project-python.sh" \
  -m tip_api.services.historical_backfill_batch_cli "$@"

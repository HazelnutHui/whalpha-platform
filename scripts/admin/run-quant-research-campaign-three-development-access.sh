#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)

exec "${repo_root}/scripts/dev/run-project-python.sh" \
  -m tip_api.services.quant_research_campaign_three_development_access_cli "$@"

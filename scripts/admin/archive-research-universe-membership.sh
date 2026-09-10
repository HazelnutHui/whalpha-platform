#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
exec "${repo_root}/scripts/dev/run-project-python.sh" \
  -m tip_api.services.research_universe_membership_archive_cli "$@"

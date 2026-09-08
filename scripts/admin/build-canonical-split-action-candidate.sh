#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "${project_root}/scripts/dev/run-project-python.sh" \
  -m tip_api.services.canonical_split_action_candidate_cli "$@"

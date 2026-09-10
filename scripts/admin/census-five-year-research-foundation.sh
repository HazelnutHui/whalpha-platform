#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$PROJECT_ROOT/scripts/dev/run-project-python.sh" \
  -m tip_api.services.five_year_research_foundation_census_cli "$@"

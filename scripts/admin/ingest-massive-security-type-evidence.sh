#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
exec .venv/bin/python -m tip_api.providers.massive.security_type_evidence "$@"

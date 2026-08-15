#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
web_dir="${repo_root}/apps/web"
snapshot_root="${repo_root}/build/private-dashboard"
bundle_root="${repo_root}/build/oci-dashboard"

usage() {
  cat <<MSG
Usage: $0 --snapshot-release RELEASE_ID [--bundle-release RELEASE_ID]

Build a versioned OCI dashboard bundle from an existing private dashboard snapshot.
No upload or deployment is performed.
MSG
}

snapshot_release=""
bundle_release=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --snapshot-release)
      snapshot_release="${2:-}"
      shift 2
      ;;
    --bundle-release)
      bundle_release="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${snapshot_release}" ]]; then
  echo "--snapshot-release is required" >&2
  usage >&2
  exit 2
fi
if [[ ! "${snapshot_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe snapshot release id" >&2
  exit 2
fi
if [[ -z "${bundle_release}" ]]; then
  bundle_release="${snapshot_release}"
fi
if [[ ! "${bundle_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe bundle release id" >&2
  exit 2
fi

snapshot_dir="${snapshot_root}/${snapshot_release}"
if [[ ! -f "${snapshot_dir}/private-data/v1/manifest.json" ]]; then
  echo "Completed snapshot manifest was not found" >&2
  exit 1
fi

bundle_dir="${bundle_root}/${bundle_release}"
staging_dir="${bundle_root}/.${bundle_release}.staging"
if [[ -e "${bundle_dir}" || -e "${staging_dir}" ]]; then
  echo "Bundle release or staging directory already exists" >&2
  exit 1
fi

mkdir -p "${bundle_root}"
mkdir -p "${staging_dir}/dashboard" "${staging_dir}/login" "${staging_dir}/private-data"

cd "${web_dir}"
VITE_MARKET_DATA_MODE=snapshot VITE_DASHBOARD_BASE=/dashboard/ npm run build >/tmp/tip_dashboard_build.log
cp -a "${web_dir}/dist/." "${staging_dir}/dashboard/"
find "${staging_dir}/dashboard" -name '*.map' -delete
cp "${web_dir}/static/login/index.html" "${staging_dir}/login/index.html"
cp "${web_dir}/static/login/login.css" "${staging_dir}/login/login.css"
cp "${web_dir}/static/login/login.js" "${staging_dir}/login/login.js"
cp -a "${snapshot_dir}/private-data/." "${staging_dir}/private-data/"

git_commit=$(cd "${repo_root}" && git rev-parse HEAD)
build_timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
file_count=$(find "${staging_dir}" -type f | wc -l)
python3 - "${staging_dir}" "${bundle_release}" "${git_commit}" "${build_timestamp}" "${file_count}" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
manifest=json.loads((root/'private-data/v1/manifest.json').read_text())
payload={
  'release_id': sys.argv[2],
  'git_commit': sys.argv[3],
  'build_timestamp': sys.argv[4],
  'frontend_mode': 'snapshot',
  'dashboard_base': '/dashboard/',
  'current_session_date': manifest['current_session_date'],
  'previous_session_date': manifest['previous_session_date'],
  'file_count': int(sys.argv[5]),
  'contains_credentials': False,
  'contains_raw_provider_data': False,
  'contains_parquet': False,
}
(root/'deployment-manifest.json').write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'))+'\n')
PY

(cd "${staging_dir}" && find . -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > checksums.sha256)
(cd "${staging_dir}" && sha256sum -c checksums.sha256 >/dev/null)
mv "${staging_dir}" "${bundle_dir}"
printf 'bundle_release=%s\n' "${bundle_release}"
printf 'bundle_dir=%s\n' "${bundle_dir}"
printf 'file_count=%s\n' "$(find "${bundle_dir}" -type f | wc -l)"

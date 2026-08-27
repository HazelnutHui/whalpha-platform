#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
web_dir="${repo_root}/apps/web"
snapshot_root="${repo_root}/build/private-dashboard"
snapshot_v2_root="/data/trading-intelligence-platform/market-data/snapshots/private-dashboard-v2/revision=universe-funnel-v2"
bundle_root="${repo_root}/build/oci-dashboard"

usage() {
  cat <<MSG
Usage: $0 (--snapshot-release RELEASE_ID | --snapshot-path ABSOLUTE_PATH) --market-intelligence-publication PUBLICATION_ID [--bundle-release RELEASE_ID]

Build a versioned OCI dashboard bundle from an existing private dashboard snapshot.
No upload or deployment is performed.
MSG
}

snapshot_release=""
snapshot_path=""
bundle_release=""
market_intelligence_publication=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --snapshot-release)
      snapshot_release="${2:-}"
      shift 2
      ;;
    --snapshot-path)
      snapshot_path="${2:-}"
      shift 2
      ;;
    --bundle-release)
      bundle_release="${2:-}"
      shift 2
      ;;
    --market-intelligence-publication)
      market_intelligence_publication="${2:-}"
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

if [[ -n "${snapshot_release}" && -n "${snapshot_path}" ]] || [[ -z "${snapshot_release}" && -z "${snapshot_path}" ]]; then
  echo "exactly one of --snapshot-release or --snapshot-path is required" >&2
  usage >&2
  exit 2
fi
if [[ -n "${snapshot_release}" && ! "${snapshot_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe snapshot release id" >&2
  exit 2
fi
if [[ -z "${bundle_release}" && -n "${snapshot_release}" ]]; then
  bundle_release="${snapshot_release}"
fi
if [[ -z "${bundle_release}" ]]; then
  echo "--bundle-release is required with --snapshot-path" >&2
  exit 2
fi
if [[ -z "${market_intelligence_publication}" ]] || [[ ! "${market_intelligence_publication}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "--market-intelligence-publication must be an explicit safe publication id" >&2
  exit 2
fi
if [[ ! "${bundle_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe bundle release id" >&2
  exit 2
fi

if [[ -n "${snapshot_path}" ]]; then
  if [[ "${snapshot_path}" != /* ]]; then
    echo "--snapshot-path must be absolute" >&2
    exit 2
  fi
  snapshot_dir=$(realpath -e -- "${snapshot_path}")
  if [[ "${snapshot_dir}" != "${snapshot_path}" || "${snapshot_dir}" != "${snapshot_v2_root}"/release_id=* ]]; then
    echo "Snapshot path is outside the approved immutable V2 namespace or contains a symlink" >&2
    exit 2
  fi
else
  snapshot_dir="${snapshot_root}/${snapshot_release}"
fi
if [[ ! -f "${snapshot_dir}/private-data/v1/manifest.json" ]]; then
  echo "Completed snapshot manifest was not found" >&2
  exit 1
fi
if [[ ! -f "${snapshot_dir}/.complete" ]]; then
  echo "Completed snapshot marker was not found" >&2
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
cp "${web_dir}/static/login/login-i18n.js" "${staging_dir}/login/login-i18n.js"
cp -a "${snapshot_dir}/private-data/." "${staging_dir}/private-data/"

git_commit=$(cd "${repo_root}" && git rev-parse HEAD)
build_timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
file_count=$(find "${staging_dir}" -type f | wc -l)
python3 - "${staging_dir}" "${bundle_release}" "${git_commit}" "${build_timestamp}" "${file_count}" "${market_intelligence_publication}" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
manifest=json.loads((root/'private-data/v1/manifest.json').read_text())
contract=(manifest.get('snapshot_contract_version'), manifest.get('dashboard_contract_version'))
if contract not in {('1.5','2.2'),('1.6','2.3'),('1.7','2.4'),('1.8','2.5')}:
  raise SystemExit('OCI bundle requires a supported Snapshot 1.5-1.8 / Dashboard 2.2-2.5 pair')
if manifest.get('market_intelligence_publication_id') != sys.argv[6]:
  raise SystemExit('snapshot Market Intelligence publication differs from explicit OCI binding')
analytics_path=root/'private-data/v1/market-regime-overviews.json'
if not analytics_path.is_file():
  raise SystemExit('snapshot Market Intelligence payload is missing')
analytics=json.loads(analytics_path.read_text())
if analytics.get('publication_id') != sys.argv[6] or len(analytics.get('records', [])) != 2:
  raise SystemExit('snapshot Market Intelligence payload binding is invalid')
if any(len(record.get('relationships', [])) != 16 for record in analytics['records']):
  raise SystemExit('snapshot does not contain all 16 ETF relationships')
candidate_fingerprint=None
candidate_audit_fingerprint=None
if contract in {('1.6','2.3'),('1.7','2.4'),('1.8','2.5')}:
  candidate_path=root/'private-data/v1'/('opportunity-candidates-summary.json' if contract == ('1.8','2.5') else 'opportunity-candidates.json')
  if not candidate_path.is_file():
    raise SystemExit('Candidate payload is missing')
  candidate=json.loads(candidate_path.read_text())
  candidate_analytics=candidate.get('analytics',{})
  candidate_source=candidate_analytics.get('source',{})
  candidate_fingerprint=manifest.get('candidate_analytics_logical_fingerprint')
  candidate_audit_fingerprint=manifest.get('candidate_audit_logical_fingerprint')
  if (manifest.get('candidate_contract_version') != 'opportunity-candidate/1.1'
      or candidate.get('publication_id') != sys.argv[6]
      or candidate.get('payload_sha256') != manifest.get('market_intelligence_payload_sha256')
      or candidate.get('payload_logical_fingerprint') != manifest.get('market_intelligence_logical_fingerprint')
      or candidate.get('candidate_analytics_logical_fingerprint') != candidate_fingerprint
      or (candidate_analytics.get('full_candidate_analytics_logical_fingerprint') if contract == ('1.8','2.5') else candidate_analytics.get('logical_fingerprint')) != candidate_fingerprint
      or candidate_source.get('candidate_audit_logical_fingerprint') != candidate_audit_fingerprint
      or candidate_source.get('candidate_parameter_fingerprint') != manifest.get('candidate_parameter_fingerprint')
      or candidate_source.get('candidate_state_parameter_fingerprint') != manifest.get('candidate_state_parameter_fingerprint')
      or len(candidate_analytics.get('universes',[{},{}])[0].get('candidates',[])) != manifest.get('candidate_primary_display_count')
      or len(candidate_analytics.get('universes',[{},{}])[1].get('candidates',[])) != manifest.get('candidate_secondary_display_count')
      or candidate_analytics.get('underlying_stock_result_not_option_return') is not True
      or candidate_analytics.get('price_volume_not_fund_flow') is not True):
    raise SystemExit('Candidate binding is invalid')
  if contract in {('1.7','2.4'),('1.8','2.5')} and (
      candidate.get('contract_version') != ('opportunity-candidate-summary-snapshot/1.0' if contract == ('1.8','2.5') else 'opportunity-candidate-snapshot/1.1')
      or candidate_analytics.get('contract_version') != ('opportunity-candidate-summary/1.0' if contract == ('1.8','2.5') else 'opportunity-candidate-publication/1.1')
      or candidate_analytics.get('leadership_rank_preserved') is not True
      or candidate_analytics.get('entry_location_separate_from_leadership') is not True
      or candidate_source.get('entry_geometry_audit_logical_fingerprint') != manifest.get('entry_geometry_audit_logical_fingerprint')
      or candidate_source.get('entry_geometry_parameter_fingerprint') != manifest.get('entry_geometry_parameter_fingerprint')
      or candidate_source.get('entry_lane_consumer_parameter_fingerprint') != manifest.get('entry_lane_consumer_parameter_fingerprint')):
    raise SystemExit('Snapshot entry-geometry binding is invalid')
  if contract == ('1.8','2.5'):
    detail_files=manifest.get('candidate_detail_files',[])
    descriptors=candidate_analytics.get('detail_shards',[])
    if (manifest.get('candidate_summary_logical_fingerprint') != candidate_analytics.get('logical_fingerprint')
        or manifest.get('candidate_summary_contract_version') != 'opportunity-candidate-summary/1.0'
        or manifest.get('candidate_detail_contract_version') != 'opportunity-candidate-detail-shard/1.0'
        or not detail_files or sorted(detail_files) != detail_files
        or sorted(item.get('filename') for item in descriptors) != detail_files
        or any(not (root/'private-data/v1'/name).is_file() for name in detail_files)):
      raise SystemExit('Snapshot 1.8 split Candidate binding is invalid')
    for descriptor in descriptors:
      detail=json.loads((root/'private-data/v1'/descriptor['filename']).read_text())
      if (detail.get('contract_version') != 'opportunity-candidate-detail-shard/1.0'
          or detail.get('publication_id') != sys.argv[6]
          or detail.get('candidate_analytics_logical_fingerprint') != candidate_fingerprint
          or detail.get('shard_id') != descriptor.get('shard_id')
          or detail.get('universe_id') != descriptor.get('universe_id')
          or detail.get('stable_id_prefix') != descriptor.get('stable_id_prefix')
          or detail.get('item_count') != descriptor.get('item_count')
          or detail.get('logical_fingerprint') != descriptor.get('logical_fingerprint')
          or len(detail.get('candidates',[])) != descriptor.get('item_count')):
        raise SystemExit('Snapshot 1.8 Candidate detail binding is invalid')
payload={
  'release_id': sys.argv[2],
  'git_commit': sys.argv[3],
  'build_timestamp': sys.argv[4],
  'frontend_mode': 'snapshot',
  'dashboard_base': '/dashboard/',
  'default_locale': 'en',
  'supported_locales': ['en','zh'],
  'market_intelligence_publication_id': sys.argv[6],
  'market_intelligence_payload_sha256': manifest['market_intelligence_payload_sha256'],
  'market_intelligence_logical_fingerprint': manifest['market_intelligence_logical_fingerprint'],
  'snapshot_contract_version': contract[0],
  'dashboard_contract_version': contract[1],
  'candidate_analytics_logical_fingerprint': candidate_fingerprint,
  'candidate_audit_logical_fingerprint': candidate_audit_fingerprint,
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

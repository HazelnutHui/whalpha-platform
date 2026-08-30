#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
web_dir="${repo_root}/apps/web"
snapshot_v2_root="/data/trading-intelligence-platform/market-data/snapshots/private-dashboard-v2/revision=universe-funnel-v2"
bundle_root="${repo_root}/build/oci-dashboard"

usage() {
  cat <<MSG
Usage: $0 --snapshot-path ABSOLUTE_PATH --market-intelligence-publication PUBLICATION_ID --bundle-release RELEASE_ID [--bundle-root ABSOLUTE_PATH] [--build-timestamp UTC]

Build a versioned OCI dashboard bundle from an existing private dashboard snapshot.
No upload or deployment is performed.
MSG
}

snapshot_path=""
bundle_release=""
market_intelligence_publication=""
build_timestamp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --bundle-root)
      bundle_root="${2:-}"
      shift 2
      ;;
    --build-timestamp)
      build_timestamp="${2:-}"
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

if [[ -z "${snapshot_path}" ]]; then
  echo "--snapshot-path is required" >&2
  usage >&2
  exit 2
fi
if [[ -z "${bundle_release}" ]]; then
  echo "--bundle-release is required" >&2
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

if [[ "${snapshot_path}" != /* ]]; then
  echo "--snapshot-path must be absolute" >&2
  exit 2
fi
snapshot_dir=$(realpath -e -- "${snapshot_path}")
if [[ "${snapshot_dir}" != "${snapshot_path}" || "${snapshot_dir}" != "${snapshot_v2_root}"/release_id=* ]]; then
  echo "Snapshot path is outside the approved immutable V2 namespace or contains a symlink" >&2
  exit 2
fi
if [[ "${bundle_root}" != /* ]]; then
  echo "--bundle-root must be absolute" >&2
  exit 2
fi
if [[ "${bundle_root}" != "${repo_root}/build/oci-dashboard" ]]; then
  if [[ "$(dirname -- "${bundle_root}")" != "/tmp" || ! "$(basename -- "${bundle_root}")" =~ ^tip-[A-Za-z0-9._-]+$ ]]; then
    echo "Explicit bundle root must be one safe direct child of /tmp" >&2
    exit 2
  fi
fi
if [[ -n "${build_timestamp}" && ! "${build_timestamp}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
  echo "--build-timestamp must be exact UTC second precision" >&2
  exit 2
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
build_log="${bundle_root}/.${bundle_release}.build.log"
if [[ -e "${bundle_dir}" || -e "${staging_dir}" || -e "${build_log}" ]]; then
  echo "Bundle release or staging directory already exists" >&2
  exit 1
fi

cd "${repo_root}"
[[ "$(hostname)" == "dell5820" ]] || { echo "must run on dell5820" >&2; exit 1; }
[[ "$(whoami)" == "hui" ]] || { echo "must run as hui" >&2; exit 1; }
[[ "$(git branch --show-current)" == "main" ]] || { echo "must run on main" >&2; exit 1; }
[[ -z "$(git status --short)" ]] || { echo "working tree must be clean" >&2; exit 1; }
git_commit=$(git rev-parse HEAD)
release_commit="${bundle_release##*-}"
[[ "${git_commit}" == "${release_commit}"* ]] || { echo "bundle release does not identify current HEAD" >&2; exit 1; }

root_created="false"
if [[ ! -e "${bundle_root}" ]]; then
  mkdir -p "${bundle_root}"
  root_created="true"
fi
[[ ! -L "${bundle_root}" && -d "${bundle_root}" ]] || { echo "bundle root is unsafe" >&2; exit 1; }
mkdir -p "${staging_dir}/dashboard" "${staging_dir}/login" "${staging_dir}/private-data"
cleanup_staging() {
  rm -rf -- "${staging_dir}"
  rm -f -- "${build_log}"
  if [[ "${root_created}" == "true" ]]; then
    rmdir -- "${bundle_root}" 2>/dev/null || true
  fi
}
trap cleanup_staging EXIT

cd "${web_dir}"
env -i \
  HOME="${HOME}" \
  PATH="${PATH}" \
  LANG="${LANG:-C.UTF-8}" \
  CI=1 \
  npm_config_offline=true \
  VITE_MARKET_DATA_MODE=snapshot \
  VITE_DASHBOARD_BASE=/dashboard/ \
  npm run build >"${build_log}"
cp -a "${web_dir}/dist/." "${staging_dir}/dashboard/"
find "${staging_dir}/dashboard" -name '*.map' -delete
cp "${web_dir}/static/login/index.html" "${staging_dir}/login/index.html"
cp "${web_dir}/static/login/login.css" "${staging_dir}/login/login.css"
cp "${web_dir}/static/login/login.js" "${staging_dir}/login/login.js"
cp "${web_dir}/static/login/login-i18n.js" "${staging_dir}/login/login-i18n.js"
cp "${web_dir}/public/favicon.png" "${staging_dir}/favicon.png"
cp -a "${snapshot_dir}/private-data/." "${staging_dir}/private-data/"

if [[ -z "${build_timestamp}" ]]; then
  build_timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fi
file_count=$(find "${staging_dir}" -type f | wc -l)
python3 - "${staging_dir}" "${bundle_release}" "${git_commit}" "${build_timestamp}" "${file_count}" "${market_intelligence_publication}" "${snapshot_dir}" <<'PY'
import hashlib, json, sys
from pathlib import Path
root=Path(sys.argv[1])
manifest=json.loads((root/'private-data/v1/manifest.json').read_text())
source_snapshot=Path(sys.argv[7])
contract=(manifest.get('snapshot_contract_version'), manifest.get('dashboard_contract_version'))
if contract not in {('1.5','2.2'),('1.6','2.3'),('1.7','2.4'),('1.8','2.5'),('1.9','2.6'),('1.10','2.7')}:
  raise SystemExit('OCI bundle requires a supported Snapshot 1.5-1.10 / Dashboard 2.2-2.7 pair')
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
strategy_fingerprint=None
strategy_audit_fingerprint=None
split_candidate=contract in {('1.8','2.5'),('1.9','2.6'),('1.10','2.7')}
if contract in {('1.6','2.3'),('1.7','2.4'),('1.8','2.5'),('1.9','2.6'),('1.10','2.7')}:
  candidate_path=root/'private-data/v1'/('opportunity-candidates-summary.json' if split_candidate else 'opportunity-candidates.json')
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
      or (candidate_analytics.get('full_candidate_analytics_logical_fingerprint') if split_candidate else candidate_analytics.get('logical_fingerprint')) != candidate_fingerprint
      or candidate_source.get('candidate_audit_logical_fingerprint') != candidate_audit_fingerprint
      or candidate_source.get('candidate_parameter_fingerprint') != manifest.get('candidate_parameter_fingerprint')
      or candidate_source.get('candidate_state_parameter_fingerprint') != manifest.get('candidate_state_parameter_fingerprint')
      or len(candidate_analytics.get('universes',[{},{}])[0].get('candidates',[])) != manifest.get('candidate_primary_display_count')
      or len(candidate_analytics.get('universes',[{},{}])[1].get('candidates',[])) != manifest.get('candidate_secondary_display_count')
      or candidate_analytics.get('underlying_stock_result_not_option_return') is not True
      or candidate_analytics.get('price_volume_not_fund_flow') is not True):
    raise SystemExit('Candidate binding is invalid')
  if contract in {('1.7','2.4'),('1.8','2.5'),('1.9','2.6'),('1.10','2.7')} and (
      candidate.get('contract_version') != ('opportunity-candidate-summary-snapshot/1.0' if split_candidate else 'opportunity-candidate-snapshot/1.1')
      or candidate_analytics.get('contract_version') != ('opportunity-candidate-summary/1.0' if split_candidate else 'opportunity-candidate-publication/1.1')
      or candidate_analytics.get('leadership_rank_preserved') is not True
      or candidate_analytics.get('entry_location_separate_from_leadership') is not True
      or candidate_source.get('entry_geometry_audit_logical_fingerprint') != manifest.get('entry_geometry_audit_logical_fingerprint')
      or candidate_source.get('entry_geometry_parameter_fingerprint') != manifest.get('entry_geometry_parameter_fingerprint')
      or candidate_source.get('entry_lane_consumer_parameter_fingerprint') != manifest.get('entry_lane_consumer_parameter_fingerprint')):
    raise SystemExit('Snapshot entry-geometry binding is invalid')
  if split_candidate:
    detail_files=manifest.get('candidate_detail_files',[])
    descriptors=candidate_analytics.get('detail_shards',[])
    if (manifest.get('candidate_summary_logical_fingerprint') != candidate_analytics.get('logical_fingerprint')
        or manifest.get('candidate_summary_contract_version') != 'opportunity-candidate-summary/1.0'
        or manifest.get('candidate_detail_contract_version') != ('opportunity-candidate-detail-shard/1.1' if contract == ('1.10','2.7') else 'opportunity-candidate-detail-shard/1.0')
        or not detail_files or sorted(detail_files) != detail_files
        or sorted(item.get('filename') for item in descriptors) != detail_files
        or any(not (root/'private-data/v1'/name).is_file() for name in detail_files)):
      raise SystemExit('Snapshot 1.8+ split Candidate binding is invalid')
    for descriptor in descriptors:
      detail=json.loads((root/'private-data/v1'/descriptor['filename']).read_text())
      if (detail.get('contract_version') != ('opportunity-candidate-detail-shard/1.1' if contract == ('1.10','2.7') else 'opportunity-candidate-detail-shard/1.0')
          or detail.get('publication_id') != sys.argv[6]
          or detail.get('candidate_analytics_logical_fingerprint') != candidate_fingerprint
          or detail.get('shard_id') != descriptor.get('shard_id')
          or detail.get('universe_id') != descriptor.get('universe_id')
          or detail.get('stable_id_prefix') != descriptor.get('stable_id_prefix')
          or detail.get('item_count') != descriptor.get('item_count')
          or detail.get('logical_fingerprint') != descriptor.get('logical_fingerprint')
          or len(detail.get('candidates',[])) != descriptor.get('item_count')):
        raise SystemExit('Snapshot 1.8+ Candidate detail binding is invalid')
      if contract == ('1.10','2.7'):
        visuals=detail.get('visual_contexts',[])
        candidates=detail.get('candidates',[])
        if (detail.get('visual_context_contract_version') != 'candidate-visual-context/1.0'
            or detail.get('visual_context_audit_logical_fingerprint') != manifest.get('candidate_visual_context_audit_logical_fingerprint')
            or len(visuals) != len(candidates)
            or [item.get('instrument_id') for item in visuals] != [item.get('instrument_id') for item in candidates]
            or any(visual.get('source_candidate_fingerprint') != candidate.get('score_logical_fingerprint')
                   or visual.get('source_entry_geometry_fingerprint') != candidate.get('entry_geometry',{}).get('logical_fingerprint')
                   for visual,candidate in zip(visuals,candidates,strict=True))):
          raise SystemExit('Snapshot 1.10 Candidate visual-context detail binding is invalid')
if contract in {('1.9','2.6'),('1.10','2.7')}:
  strategy_file=manifest.get('candidate_strategy_file')
  strategy_path=root/'private-data/v1'/str(strategy_file)
  if strategy_file != 'candidate-strategy-channels.json' or not strategy_path.is_file():
    raise SystemExit('Snapshot 1.9 strategy-channel payload is missing')
  raw_strategy=strategy_path.read_bytes()
  strategy=json.loads(raw_strategy)
  strategy_source=strategy.get('source',{})
  strategy_fingerprint=manifest.get('candidate_strategy_logical_fingerprint')
  strategy_audit_fingerprint=manifest.get('candidate_strategy_audit_logical_fingerprint')
  channel_order=['momentum_breakout','strong_stock_pullback','trend_continuation','technical_reversal','fundamental_value_reversal','defensive_rotation']
  universe_order=manifest.get('available_universe_ids')
  logical_payload=dict(strategy)
  logical_payload.pop('logical_fingerprint',None)
  actual_logical=hashlib.sha256(json.dumps(logical_payload,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
  if (manifest.get('candidate_strategy_contract_version') != 'candidate-strategy-channel-product/1.0'
      or hashlib.sha256(raw_strategy).hexdigest() != manifest.get('file_sha256',{}).get(strategy_file)
      or strategy.get('contract_version') != 'candidate-strategy-channel-product/1.0'
      or strategy.get('logical_fingerprint') != strategy_fingerprint
      or actual_logical != strategy_fingerprint
      or strategy.get('as_of_session') != manifest.get('current_session_date')
      or strategy.get('default_universe_id') != manifest.get('default_universe_id')
      or strategy.get('universe_order') != universe_order
      or strategy.get('channel_order') != channel_order
      or strategy.get('fixed_baseline_not_chronologically_validated') is not True
      or strategy.get('cross_channel_score_comparison_prohibited') is not True
      or strategy.get('market_fit_separate_and_unvalidated') is not True
      or strategy.get('research_priority_only') is not True
      or strategy.get('underlying_stock_result_not_option_return') is not True
      or strategy.get('price_volume_not_fund_flow') is not True
      or strategy.get('guest_and_credential_capability_identical') is not True
      or strategy_source.get('strategy_audit_manifest_sha256') != manifest.get('candidate_strategy_audit_manifest_sha256')
      or strategy_source.get('strategy_audit_logical_fingerprint') != strategy_audit_fingerprint
      or strategy_source.get('strategy_parameter_fingerprint') != manifest.get('candidate_strategy_parameter_fingerprint')
      or strategy_source.get('candidate_analytics_logical_fingerprint') != candidate_fingerprint
      or strategy_source.get('candidate_audit_logical_fingerprint') != candidate_audit_fingerprint
      or strategy_source.get('entry_geometry_audit_logical_fingerprint') != manifest.get('entry_geometry_audit_logical_fingerprint')
      or strategy_source.get('strategy_oracle_mismatch_count') != 0
      or strategy_source.get('strategy_input_permutation_match') is not True
      or strategy_source.get('strategy_oracle_production_calculator_imported') is not False
      or strategy_source.get('external_request_count') != 0
      or strategy_source.get('production_write_count') != 0):
    raise SystemExit('Snapshot 1.9 strategy-channel binding is invalid')
  universes=strategy.get('universes',[])
  batch_fingerprints=strategy_source.get('strategy_batch_fingerprints',[])
  consumer_fingerprints=strategy_source.get('strategy_consumer_fingerprints',[])
  if len(universes) != 2 or len(batch_fingerprints) != 2 or len(consumer_fingerprints) != 2:
    raise SystemExit('Snapshot 1.9 strategy-channel Universe sources are incomplete')
  for universe_index,(universe,universe_id) in enumerate(zip(universes,universe_order,strict=True)):
    if (universe.get('contract_version') != 'candidate-strategy-channel-consumer/1.0'
        or universe.get('universe_id') != universe_id
        or universe.get('as_of_session') != manifest.get('current_session_date')
        or universe.get('channel_order') != channel_order
        or universe.get('source_batch_logical_fingerprint') != batch_fingerprints[universe_index]
        or universe.get('logical_fingerprint') != consumer_fingerprints[universe_index]
        or universe.get('cross_channel_score_prohibited') is not True
        or universe.get('shadow_only') is not True
        or len(universe.get('channels',[])) != 6):
      raise SystemExit('Snapshot 1.9 strategy-channel consumer binding is invalid')
    population_count=None
    for channel_index,(channel,channel_id) in enumerate(zip(universe['channels'],channel_order,strict=True)):
      counts=channel.get('status_counts',{})
      count_total=sum(counts.values()) if isinstance(counts,dict) and all(isinstance(value,int) and value >= 0 for value in counts.values()) else -1
      qualifying=counts.get('advance_to_research',0)+counts.get('watch_for_trigger',0) if count_total >= 0 else -1
      records=channel.get('displayed_records',[])
      if population_count is None: population_count=count_total
      if (channel.get('channel') != channel_id or channel.get('display_cap') != 8
          or count_total <= 0 or count_total != population_count
          or channel.get('qualifying_count') != qualifying
          or not isinstance(records,list) or len(records) != min(qualifying,8)):
        raise SystemExit('Snapshot 1.9 strategy-channel counts are invalid')
      for rank,item in enumerate(records,start=1):
        if (item.get('universe_id') != universe_id or item.get('channel') != channel_id
            or item.get('as_of_session') != manifest.get('current_session_date')
            or item.get('within_channel_rank') != rank
            or item.get('status') not in {'advance_to_research','watch_for_trigger'}
            or item.get('score_meaning') != 'within_channel_research_priority_not_return_probability'
            or item.get('market_fit_separate_from_channel_score') is not True
            or item.get('first_rejection_is_risk_not_status_reason') is not True):
          raise SystemExit('Snapshot 1.9 strategy-channel rank or decision boundary is invalid')
if contract == ('1.10','2.7'):
  visual_fingerprints=manifest.get('candidate_visual_context_batch_fingerprints',[])
  if (manifest.get('candidate_visual_context_contract_version') != 'candidate-visual-context/1.0'
      or not isinstance(visual_fingerprints,list) or len(visual_fingerprints) != 2
      or any(not isinstance(value,str) or len(value) != 64 for value in [
        manifest.get('candidate_visual_context_audit_manifest_sha256'),
        manifest.get('candidate_visual_context_audit_logical_fingerprint'),
        *visual_fingerprints])):
    raise SystemExit('Snapshot 1.10 Candidate visual-context manifest binding is invalid')
source_files=[]
for path in sorted(source_snapshot.rglob('*')):
  if path.is_symlink():
    raise SystemExit('Source Snapshot contains a symlink')
  if path.is_file():
    source_files.append({'relative_path':path.relative_to(source_snapshot).as_posix(),'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
snapshot_aggregate_sha256=hashlib.sha256(json.dumps(source_files,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
payload={
  'bundle_contract_version': 'oci-dashboard-serving-bundle/1.0',
  'release_id': sys.argv[2],
  'git_commit': sys.argv[3],
  'source_tree_clean': True,
  'build_timestamp': sys.argv[4],
  'frontend_mode': 'snapshot',
  'dashboard_base': '/dashboard/',
  'default_locale': 'en',
  'supported_locales': ['en','zh'],
  'guest_and_credential_capability_identical': True,
  'market_intelligence_publication_id': sys.argv[6],
  'market_intelligence_payload_sha256': manifest['market_intelligence_payload_sha256'],
  'market_intelligence_logical_fingerprint': manifest['market_intelligence_logical_fingerprint'],
  'snapshot_contract_version': contract[0],
  'dashboard_contract_version': contract[1],
  'snapshot_aggregate_sha256': snapshot_aggregate_sha256,
  'snapshot_manifest_sha256': hashlib.sha256((source_snapshot/'private-data/v1/manifest.json').read_bytes()).hexdigest(),
  'candidate_analytics_logical_fingerprint': candidate_fingerprint,
  'candidate_audit_logical_fingerprint': candidate_audit_fingerprint,
  'candidate_strategy_logical_fingerprint': strategy_fingerprint,
  'candidate_strategy_audit_logical_fingerprint': strategy_audit_fingerprint,
  'candidate_visual_context_audit_logical_fingerprint': manifest.get('candidate_visual_context_audit_logical_fingerprint'),
  'current_session_date': manifest['current_session_date'],
  'previous_session_date': manifest['previous_session_date'],
  'file_count': int(sys.argv[5]),
  'contains_credentials': False,
  'contains_raw_provider_data': False,
  'contains_parquet': False,
  'deployment_authorized': False,
}
payload['bundle_logical_fingerprint']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
(root/'deployment-manifest.json').write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'))+'\n')
PY

(cd "${staging_dir}" && find . -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > checksums.sha256)
(cd "${staging_dir}" && sha256sum -c checksums.sha256 >/dev/null)
mv "${staging_dir}" "${bundle_dir}"
rm -f -- "${build_log}"
trap - EXIT
printf 'bundle_release=%s\n' "${bundle_release}"
printf 'bundle_dir=%s\n' "${bundle_dir}"
printf 'file_count=%s\n' "$(find "${bundle_dir}" -type f | wc -l)"

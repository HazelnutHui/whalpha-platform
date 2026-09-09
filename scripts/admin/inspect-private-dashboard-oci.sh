#!/usr/bin/env bash
set -euo pipefail

remote_alias="whalpha-oci"
remote_base="/srv/whalpha"
target_release=""

usage() {
  cat <<MSG
Usage: $0 --target-release RELEASE_ID

Reads non-secret OCI release, service, listener, protection, and temporary guest
Session evidence. It never deploys, reloads, rolls back, or reads credentials.
MSG
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-release)
      target_release="${2:-}"
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

if [[ ! "${target_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe target release id" >&2
  exit 2
fi

[[ "$(hostname)" == "dell5820" ]] || { echo "must run on dell5820" >&2; exit 1; }
[[ "$(whoami)" == "hui" ]] || { echo "must run as hui" >&2; exit 1; }

ssh "${remote_alias}" bash -s -- "${target_release}" "${remote_base}" <<'REMOTE'
set -euo pipefail
target_release="$1"
remote_base="$2"
[[ "$(hostname)" == "hui" ]] || { echo "remote hostname mismatch" >&2; exit 1; }
[[ "$(whoami)" == "ubuntu" ]] || { echo "remote user mismatch" >&2; exit 1; }
sudo -n true >/dev/null

current_release=""
manifest_sha=""
checksums_sha=""
bundle_fingerprint=""
source_revision=""
snapshot_manifest_sha=""
if [[ -L "${remote_base}/current" ]]; then
  current_path=$(readlink -f "${remote_base}/current")
  expected_prefix="${remote_base}/releases/"
  [[ "${current_path}" == "${expected_prefix}"* ]] || { echo "current target is outside releases" >&2; exit 1; }
  current_release="${current_path#${expected_prefix}}"
  [[ "${current_release}" != */* ]] || { echo "current release path is nested" >&2; exit 1; }
  (cd "${current_path}" && sha256sum -c checksums.sha256 >/dev/null)
  manifest_sha=$(sha256sum "${current_path}/deployment-manifest.json" | awk '{print $1}')
  checksums_sha=$(sha256sum "${current_path}/checksums.sha256" | awk '{print $1}')
  readarray -t manifest_values < <(python3 - "${current_path}/deployment-manifest.json" <<'PY'
import json,sys
value=json.load(open(sys.argv[1],encoding="utf-8"))
print(value["bundle_logical_fingerprint"])
print(value["git_commit"])
print(value["snapshot_manifest_sha256"])
PY
)
  bundle_fingerprint="${manifest_values[0]}"
  source_revision="${manifest_values[1]}"
  snapshot_manifest_sha="${manifest_values[2]}"
elif [[ -e "${remote_base}/current" ]]; then
  echo "current is not a symlink" >&2
  exit 1
fi

target_exists=false
[[ -e "${remote_base}/releases/${target_release}" ]] && target_exists=true
mapfile -t staging_ids < <(sudo find "${remote_base}" -maxdepth 1 -mindepth 1 -name '.staging-*' -printf '%f\n' 2>/dev/null | sed 's/^\.staging-//' | sort -u)
mapfile -t failed_ids < <(sudo find "${remote_base}/releases" -mindepth 2 -maxdepth 2 -type f -name DEPLOY_FAILED -printf '%h\n' 2>/dev/null | sed 's#^.*/##' | sort -u)

nginx_active=false
nginx_enabled=false
auth_active=false
auth_enabled=false
systemctl is-active --quiet nginx && nginx_active=true
systemctl is-enabled --quiet nginx && nginx_enabled=true
systemctl is-active --quiet whalpha-dashboard-auth.service && auth_active=true
systemctl is-enabled --quiet whalpha-dashboard-auth.service && auth_enabled=true
failed_units=$(systemctl --failed --no-legend | wc -l)

auth_local=true
if ! ss -ltn sport = :8010 | awk 'NR>1 {print $4}' | grep -Eq '^(127\.0\.0\.1|\[::ffff:127\.0\.0\.1\]):8010$'; then
  auth_local=false
fi
if ss -ltn sport = :8010 | awk 'NR>1 {print $4}' | grep -vE '^(127\.0\.0\.1|\[::ffff:127\.0\.0\.1\]):8010$' | grep -q .; then
  auth_local=false
fi
unexpected_listener=false
if ss -ltn | awk '{print $4}' | grep -Eq ':(8000|8001)$'; then
  unexpected_listener=true
fi

protected=false
dashboard_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -o /dev/null -w '%{http_code}' https://whalpha.com/dashboard/ || true)
private_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -o /dev/null -w '%{http_code}' https://whalpha.com/private-data/v1/manifest.json || true)
status_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -o /dev/null -w '%{http_code}' https://whalpha.com/auth/status || true)
internal_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -o /dev/null -w '%{http_code}' https://whalpha.com/auth/internal-verify || true)
if [[ "${dashboard_code}" == "302" && "${private_code}" == "401" && "${status_code}" == "401" && "${internal_code}" == "404" ]]; then
  protected=true
fi

guest_verified=false
route_parity=false
guest_jar=$(mktemp)
guest_body=$(mktemp)
guest_dashboard=$(mktemp)
guest_private=$(mktemp)
cleanup() {
  rm -f "${guest_jar}" "${guest_body}" "${guest_dashboard}" "${guest_private}"
}
trap cleanup EXIT
guest_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -c "${guest_jar}" -o "${guest_body}" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Origin: https://whalpha.com' --data '{"next":"/dashboard/"}' https://whalpha.com/auth/guest || true)
guest_dashboard_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -b "${guest_jar}" -o "${guest_dashboard}" -w '%{http_code}' https://whalpha.com/dashboard/ || true)
guest_private_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -b "${guest_jar}" -o "${guest_private}" -w '%{http_code}' https://whalpha.com/private-data/v1/manifest.json || true)
guest_logout_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -b "${guest_jar}" -o /dev/null -w '%{http_code}' -X POST https://whalpha.com/auth/logout || true)
guest_private_sha=$(sha256sum "${guest_private}" | awk '{print $1}')
if [[ "${guest_code}" == "200" && "${guest_dashboard_code}" == "200" && "${guest_private_code}" == "200" && "${guest_logout_code}" == "303" && "${guest_private_sha}" == "${snapshot_manifest_sha}" ]] && grep -q '"authenticated":true' "${guest_body}" && grep -q '<div id="root"></div>' "${guest_dashboard}"; then
  guest_verified=true
fi
manifest_parity=$(python3 - "${remote_base}/current/deployment-manifest.json" <<'PY'
import json,sys
try:
  value=json.load(open(sys.argv[1],encoding="utf-8"))
  print("true" if value.get("guest_and_credential_capability_identical") is True else "false")
except Exception:
  print("false")
PY
)
if [[ "${guest_verified}" == "true" && "${manifest_parity}" == "true" ]] && sudo grep -q 'auth_request /auth/internal-verify;' /etc/nginx/sites-available/whalpha.com; then
  route_parity=true
fi

python3 - "${target_release}" "${current_release}" "${manifest_sha}" "${checksums_sha}" "${bundle_fingerprint}" "${source_revision}" "${target_exists}" "${nginx_active}" "${nginx_enabled}" "${auth_active}" "${auth_enabled}" "${auth_local}" "${unexpected_listener}" "${protected}" "${guest_verified}" "${route_parity}" "${failed_units}" "${staging_ids[*]}" "${failed_ids[*]}" <<'PY'
import datetime,hashlib,json,sys
(
 target,current,manifest_sha,checksums_sha,bundle_fp,source_revision,target_exists,
 nginx_active,nginx_enabled,auth_active,auth_enabled,auth_local,unexpected,
 protected,guest,parity,failed_units,staging,failed
)=sys.argv[1:]
boolean=lambda value: value == "true"
base={
 "contract_version":"oci-dashboard-remote-state/1.0",
 "inspected_at":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
 "inspected_target_release":target,
 "remote_host":"hui",
 "remote_user":"ubuntu",
 "remote_base":"/srv/whalpha",
 "current_release_id":current or None,
 "current_manifest_sha256":manifest_sha or None,
 "current_checksums_sha256":checksums_sha or None,
 "current_bundle_logical_fingerprint":bundle_fp or None,
 "current_source_revision":source_revision or None,
 "target_release_exists":boolean(target_exists),
 "staging_release_ids":sorted(set(staging.split())) if staging else [],
 "failed_release_ids":sorted(set(failed.split())) if failed else [],
 "nginx_active":boolean(nginx_active),
 "nginx_enabled":boolean(nginx_enabled),
 "auth_service_active":boolean(auth_active),
 "auth_service_enabled":boolean(auth_enabled),
 "auth_listener_localhost_only":boolean(auth_local),
 "unexpected_private_listener":boolean(unexpected),
 "protected_routes_verified":boolean(protected),
 "guest_session_verified":boolean(guest),
 "guest_and_credential_route_policy_identical":boolean(parity),
 "credential_login_tested":False,
 "failed_system_unit_count":int(failed_units),
}
logical={key:value for key,value in base.items() if key != "inspected_at"}
base["state_fingerprint"]=hashlib.sha256(json.dumps(logical,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
print(json.dumps(base,sort_keys=True,separators=(",",":"),ensure_ascii=True))
PY
REMOTE

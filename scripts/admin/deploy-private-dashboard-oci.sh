#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
bundle_root="${repo_root}/build/oci-dashboard"
nginx_template="${repo_root}/deploy/oci/nginx/whalpha-private-dashboard.conf.template"
remote_alias="whalpha-oci"
remote_base="/srv/whalpha"
remote_site_available="/etc/nginx/sites-available/whalpha.com"
remote_site_enabled="/etc/nginx/sites-enabled/whalpha.com"
auth_file="/etc/nginx/auth/whalpha-dashboard.htpasswd"

usage() {
  cat <<MSG
Usage: $0 --bundle-release RELEASE_ID [--dry-run]
       $0 --bundle-release RELEASE_ID --apply

Default is dry-run. Apply uploads one completed static Dashboard bundle to the
reviewed OCI host, protects /dashboard/ and /private-data/ with the existing
server-side Basic Auth file, and verifies unauthenticated private paths return
401. It never accepts or tests a Dashboard password.
MSG
}

bundle_release=""
apply="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-release)
      bundle_release="${2:-}"
      shift 2
      ;;
    --dry-run)
      apply="false"
      shift
      ;;
    --apply)
      apply="true"
      shift
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

if [[ -z "${bundle_release}" ]]; then
  echo "--bundle-release is required" >&2
  usage >&2
  exit 2
fi
if [[ ! "${bundle_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe bundle release id" >&2
  exit 2
fi

cd "${repo_root}"
[[ "$(hostname)" == "dell5820" ]] || { echo "must run on dell5820" >&2; exit 1; }
[[ "$(whoami)" == "hui" ]] || { echo "must run as hui" >&2; exit 1; }
[[ "$(git branch --show-current)" == "main" ]] || { echo "must run on main" >&2; exit 1; }
[[ -z "$(git status --short)" ]] || { echo "working tree must be clean" >&2; exit 1; }
[[ -f "${nginx_template}" ]] || { echo "Nginx template missing" >&2; exit 1; }

bundle_dir="${bundle_root}/${bundle_release}"
[[ -f "${bundle_dir}/deployment-manifest.json" ]] || { echo "bundle manifest missing" >&2; exit 1; }
[[ -f "${bundle_dir}/checksums.sha256" ]] || { echo "bundle checksums missing" >&2; exit 1; }
(cd "${bundle_dir}" && sha256sum -c checksums.sha256 >/dev/null)

manifest_commit=$("${repo_root}/.venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["git_commit"])' "${bundle_dir}/deployment-manifest.json")
current_commit=$(git rev-parse HEAD)
[[ "${manifest_commit}" == "${current_commit}" ]] || { echo "bundle git commit does not match current HEAD" >&2; exit 1; }

echo "mode=$([[ "${apply}" == "true" ]] && echo apply || echo dry-run)"
echo "bundle_release=${bundle_release}"
echo "remote_alias=${remote_alias}"

ssh "${remote_alias}" bash -s -- "${auth_file}" "${remote_base}" <<'REMOTE'
set -euo pipefail
auth_file="$1"
remote_base="$2"
[[ "$(hostname)" == "hui" ]] || { echo "remote hostname mismatch" >&2; exit 1; }
[[ "$(whoami)" == "ubuntu" ]] || { echo "remote user mismatch" >&2; exit 1; }
sudo -n true >/dev/null
systemctl is-active --quiet nginx
systemctl is-enabled --quiet nginx
sudo nginx -t >/dev/null
stat_line=$(sudo stat -c 'owner=%U:%G|mode=%a|type=%F' "${auth_file}")
case "${stat_line}" in
  owner=root:www-data\|mode=600\|type=regular\ file|owner=root:www-data\|mode=640\|type=regular\ file) ;;
  *) echo "auth file metadata mismatch: ${stat_line}" >&2; exit 1 ;;
esac
sudo awk -F: '$1=="hui"{found=1} END{exit found?0:1}' "${auth_file}"
if [[ -e "${remote_base}/current" && ! -L "${remote_base}/current" ]]; then
  echo "unexpected non-symlink current path" >&2
  exit 1
fi
if ss -ltn | awk '{print $4}' | grep -Eq ':(8000|8001)$'; then
  echo "unexpected private backend listener" >&2
  exit 1
fi
df -Pk /srv /tmp >/dev/null
echo "remote_preflight=ok"
REMOTE

if [[ "${apply}" != "true" ]]; then
  echo "dry_run_only=true"
  exit 0
fi

tmp_name="whalpha-dashboard-${bundle_release}"
local_tar="/tmp/${tmp_name}.tar.gz"
remote_tar="/tmp/${tmp_name}.tar.gz"
remote_template="/tmp/${tmp_name}.nginx.conf"
rm -f "${local_tar}"
tar -C "${bundle_dir}" -czf "${local_tar}" .
scp "${local_tar}" "${remote_alias}:${remote_tar}" >/dev/null
scp "${nginx_template}" "${remote_alias}:${remote_template}" >/dev/null
rm -f "${local_tar}"

ssh "${remote_alias}" bash -s -- "${bundle_release}" "${remote_tar}" "${remote_template}" "${remote_base}" "${remote_site_available}" "${remote_site_enabled}" <<'REMOTE'
set -euo pipefail
release_id="$1"
remote_tar="$2"
remote_template="$3"
remote_base="$4"
site_available="$5"
site_enabled="$6"
release_dir="${remote_base}/releases/${release_id}"
stage_dir="${remote_base}/.staging-${release_id}"
extract_dir="/tmp/whalpha-dashboard-${release_id}.extract"
backup_config="${site_available}.pre-dashboard-${release_id}"
previous_current=""

rollback() {
  status=$?
  if [[ ${status} -ne 0 ]]; then
    echo "deploy_failed=true" >&2
    if [[ -n "${previous_current}" && -e "${previous_current}" ]]; then
      sudo ln -sfn "${previous_current}" "${remote_base}/current.rollback"
      sudo mv -Tf "${remote_base}/current.rollback" "${remote_base}/current"
    elif [[ -L "${remote_base}/current" ]]; then
      sudo rm -f "${remote_base}/current"
    fi
    if [[ -d "${release_dir}" ]]; then
      sudo touch "${release_dir}/DEPLOY_FAILED"
    fi
    if [[ -f "${backup_config}" ]]; then
      sudo cp "${backup_config}" "${site_available}"
      sudo nginx -t >/dev/null && sudo systemctl reload nginx || true
    fi
  fi
  rm -rf "${extract_dir}"
  rm -f "${remote_tar}" "${remote_template}"
  exit ${status}
}
trap rollback EXIT

[[ "$(hostname)" == "hui" ]]
[[ "$(whoami)" == "ubuntu" ]]
[[ ! -e "${release_dir}" ]] || { echo "target release already exists" >&2; exit 1; }
rm -rf "${extract_dir}"
mkdir -p "${extract_dir}"
tar -xzf "${remote_tar}" -C "${extract_dir}"
(cd "${extract_dir}" && sha256sum -c checksums.sha256 >/dev/null)
test -f "${extract_dir}/dashboard/index.html"
test -f "${extract_dir}/private-data/v1/manifest.json"
test -f "${extract_dir}/deployment-manifest.json"
test -f "${extract_dir}/checksums.sha256"
if find "${extract_dir}" \( -name '.env' -o -name '*.pem' -o -name '*key*' -o -name '*.parquet' -o -name '*.map' \) | grep -q .; then
  echo "bundle contains forbidden file pattern" >&2
  exit 1
fi

sudo mkdir -p "${remote_base}/releases"
if [[ -L "${remote_base}/current" ]]; then
  previous_current=$(readlink -f "${remote_base}/current")
fi
sudo rm -rf "${stage_dir}"
sudo mkdir -p "${stage_dir}"
sudo cp -a "${extract_dir}/." "${stage_dir}/"
sudo chown -R root:www-data "${stage_dir}"
sudo find "${stage_dir}" -type d -exec chmod 755 {} +
sudo find "${stage_dir}" -type f -exec chmod 644 {} +
sudo mv "${stage_dir}" "${release_dir}"

if [[ -f "${site_available}" ]]; then
  sudo cp "${site_available}" "${backup_config}"
fi
sudo cp "${remote_template}" "${site_available}"
if [[ ! -e "${site_enabled}" ]]; then
  sudo ln -s "${site_available}" "${site_enabled}"
fi
sudo ln -sfn "${release_dir}" "${remote_base}/current.new"
sudo mv -Tf "${remote_base}/current.new" "${remote_base}/current"
sudo nginx -t >/dev/null
sudo systemctl reload nginx

public_body=$(mktemp)
private_body=$(mktemp)
public_code=$(curl -sS -o "${public_body}" -w '%{http_code}' https://whalpha.com/)
[[ "${public_code}" == "200" ]] || { echo "public https failed" >&2; exit 1; }
grep -q 'WH Alpha' "${public_body}"
grep -q 'Trading Intelligence Platform' "${public_body}"
grep -q 'New platform under development' "${public_body}"
dashboard_code=$(curl -sS -o "${private_body}" -w '%{http_code}' https://whalpha.com/dashboard/)
[[ "${dashboard_code}" == "401" ]] || { echo "dashboard unauth status ${dashboard_code}" >&2; exit 1; }
private_code=$(curl -sS -o "${private_body}" -w '%{http_code}' https://whalpha.com/private-data/v1/manifest.json)
[[ "${private_code}" == "401" ]] || { echo "private-data unauth status ${private_code}" >&2; exit 1; }
http_code=$(curl -sS -o /dev/null -w '%{http_code}' http://whalpha.com/)
[[ "${http_code}" == "301" || "${http_code}" == "308" ]] || { echo "http redirect status ${http_code}" >&2; exit 1; }
for path in /dashboard /dashboard/index.html /private-data /private-data/ /private-data/v1/manifest.json /private-data/%2e%2e/dashboard/index.html /.env /deployment-manifest.json /checksums.sha256; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' "https://whalpha.com${path}")
  case "${path}:${code}" in
    /dashboard:401|/dashboard:301|/dashboard:308|/dashboard/index.html:401|/private-data:401|/private-data/:401|/private-data/:403|/private-data/v1/manifest.json:401|/private-data/%2e%2e/dashboard/index.html:400|/private-data/%2e%2e/dashboard/index.html:401|/.env:403|/.env:404|/deployment-manifest.json:404|/checksums.sha256:404) ;;
    *) echo "unexpected bypass result ${path} ${code}" >&2; exit 1 ;;
  esac
done
curl -sS -I https://whalpha.com/dashboard/ | grep -qi '^WWW-Authenticate:'
curl -sS -I https://whalpha.com/private-data/v1/manifest.json | grep -qi '^Cache-Control:.*no-store'
rm -f "${public_body}" "${private_body}"
systemctl is-active --quiet nginx
[[ "$(systemctl --failed --no-legend | wc -l)" == "0" ]]
if ss -ltn | awk '{print $4}' | grep -Eq ':(8000|8001)$'; then
  echo "unexpected private backend listener after deploy" >&2
  exit 1
fi
(cd "${release_dir}" && sha256sum -c checksums.sha256 >/dev/null)
echo "apply=ok"
echo "deployment_status=deployed_pending_manual_authenticated_verification"
trap - EXIT
rm -rf "${extract_dir}"
rm -f "${remote_tar}" "${remote_template}"
REMOTE

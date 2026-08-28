#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
bundle_root="${repo_root}/build/oci-dashboard"
nginx_template="${repo_root}/deploy/oci/nginx/whalpha-private-dashboard.conf.template"
auth_service_source="${repo_root}/deploy/oci/auth/whalpha_auth_service.py"
password_rotation_source="${repo_root}/scripts/admin/rotate-whalpha-dashboard-password.sh"
remote_alias="whalpha-oci"
remote_base="/srv/whalpha"
remote_site_available="/etc/nginx/sites-available/whalpha.com"
remote_site_enabled="/etc/nginx/sites-enabled/whalpha.com"
auth_file="/etc/nginx/auth/whalpha-dashboard.htpasswd"
auth_service_path="/srv/whalpha/auth/whalpha_auth_service.py"
auth_unit_path="/etc/systemd/system/whalpha-dashboard-auth.service"
remote_admin_dir="/srv/whalpha/admin"
remote_password_rotation_path="${remote_admin_dir}/rotate-whalpha-dashboard-password.sh"

usage() {
  cat <<MSG
Usage: $0 --bundle-release RELEASE_ID [--dry-run]
       $0 --bundle-release RELEASE_ID --apply

Default is dry-run. Apply uploads one completed static Dashboard bundle, the
localhost-only Session Auth Service, and the password-rotation admin helper to
the reviewed OCI host. It verifies that / is the branded credential/guest
entry, /dashboard/ and /private-data/ reject missing Sessions, and a
temporary guest Session reads the same protected Dashboard and Snapshot before
logout. It never accepts or tests a Dashboard password.
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
[[ -f "${auth_service_source}" ]] || { echo "Auth service source missing" >&2; exit 1; }
[[ -f "${password_rotation_source}" ]] || { echo "password rotation script missing" >&2; exit 1; }

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
sudo test -s "${auth_file}"
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
remote_auth_service="/tmp/${tmp_name}.auth.py"
remote_password_rotation="/tmp/${tmp_name}.rotate-password.sh"
rm -f "${local_tar}"
tar -C "${bundle_dir}" -czf "${local_tar}" .
scp "${local_tar}" "${remote_alias}:${remote_tar}" >/dev/null
scp "${nginx_template}" "${remote_alias}:${remote_template}" >/dev/null
scp "${auth_service_source}" "${remote_alias}:${remote_auth_service}" >/dev/null
scp "${password_rotation_source}" "${remote_alias}:${remote_password_rotation}" >/dev/null
rm -f "${local_tar}"

ssh "${remote_alias}" bash -s -- "${bundle_release}" "${remote_tar}" "${remote_template}" "${remote_auth_service}" "${remote_password_rotation}" "${remote_base}" "${remote_site_available}" "${remote_site_enabled}" "${auth_service_path}" "${auth_unit_path}" "${auth_file}" "${remote_admin_dir}" "${remote_password_rotation_path}" <<'REMOTE'
set -euo pipefail
release_id="$1"
remote_tar="$2"
remote_template="$3"
remote_auth_service="$4"
remote_password_rotation="$5"
remote_base="$6"
site_available="$7"
site_enabled="$8"
auth_service_path="$9"
auth_unit_path="${10}"
auth_file="${11}"
remote_admin_dir="${12}"
remote_password_rotation_path="${13}"
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
  rm -f "${remote_tar}" "${remote_template}" "${remote_auth_service}" "${remote_password_rotation}"
  rm -f "${guest_headers:-}" "${guest_body:-}" "${guest_cookie_jar:-}" "${guest_dashboard_body:-}" "${guest_private_body:-}" "${guest_candidate_body:-}" "${guest_candidate_detail_body:-}" "${guest_strategy_body:-}"
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
test -f "${extract_dir}/login/index.html"
test -f "${extract_dir}/login/login.css"
test -f "${extract_dir}/login/login.js"
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

sudo mkdir -p "$(dirname "${auth_service_path}")"
sudo cp "${remote_auth_service}" "${auth_service_path}"
sudo chown root:root "${auth_service_path}"
sudo chmod 644 "${auth_service_path}"
sudo mkdir -p "${remote_admin_dir}"
sudo cp "${remote_password_rotation}" "${remote_password_rotation_path}"
sudo chown root:root "${remote_password_rotation_path}"
sudo chmod 755 "${remote_password_rotation_path}"
sudo tee "${auth_unit_path}" >/dev/null <<UNIT
[Unit]
Description=WH Alpha Dashboard Session Auth Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/bin/python3 ${auth_service_path} --host 127.0.0.1 --port 8010 --htpasswd ${auth_file}
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadOnlyPaths=/etc/nginx/auth
ReadOnlyPaths=/srv/whalpha/auth

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now whalpha-dashboard-auth.service >/dev/null
sudo systemctl restart whalpha-dashboard-auth.service
auth_ready=false
for _ in 1 2 3 4 5 6 7 8 9 10; do
  code=$(curl -sS -o /dev/null -w %{http_code} http://127.0.0.1:8010/check 2>/dev/null || true)
  if [[ "${code}" == "401" ]]; then
    auth_ready=true
    break
  fi
  sleep 1
done
[[ "${auth_ready}" == "true" ]] || { echo "auth service did not become ready" >&2; exit 1; }
wrong_headers=$(mktemp)
wrong_body=$(mktemp)
wrong_code=$(curl -sS -D "${wrong_headers}" -o "${wrong_body}" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Origin: https://whalpha.com' -H 'Host: whalpha.com' --data '{"username":"invalid-test-user","password":"invalid-test-password","next":"/dashboard/"}' http://127.0.0.1:8010/login)
[[ "${wrong_code}" == "401" ]] || { echo "wrong-password JSON login did not fail safely" >&2; exit 1; }
grep -q '"error":"invalid_credentials"' "${wrong_body}" || { echo "wrong-password JSON login did not return generic failure" >&2; exit 1; }
if grep -qi '^Set-Cookie:' "${wrong_headers}" || grep -q 'invalid-test-password' "${wrong_body}" || grep -q 'invalid-test-user' "${wrong_body}"; then
  echo "wrong-password JSON login leaked credential material" >&2
  exit 1
fi
rm -f "${wrong_headers}" "${wrong_body}"
guest_headers=$(mktemp)
guest_body=$(mktemp)
guest_code=$(curl -sS -D "${guest_headers}" -o "${guest_body}" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Origin: https://whalpha.com' -H 'Host: whalpha.com' --data '{"next":"/dashboard/?view=regime&lang=en"}' http://127.0.0.1:8010/guest)
[[ "${guest_code}" == "200" ]] || { echo "localhost guest Session status ${guest_code}" >&2; exit 1; }
grep -q '"authenticated":true' "${guest_body}" || { echo "localhost guest Session did not authenticate" >&2; exit 1; }
guest_cookie=$(awk 'BEGIN{IGNORECASE=1} /^Set-Cookie:/ {sub(/^[^:]+:[[:space:]]*/, ""); sub(/;.*/, ""); print; exit}' "${guest_headers}" | tr -d '\r')
[[ "${guest_cookie}" == __Host-whalpha_session=* ]] || { echo "localhost guest Session cookie missing" >&2; exit 1; }
guest_check_code=$(curl -sS -o /dev/null -w '%{http_code}' -H "Cookie: ${guest_cookie}" http://127.0.0.1:8010/check)
[[ "${guest_check_code}" == "200" ]] || { echo "localhost guest Session did not pass shared auth check" >&2; exit 1; }
curl -sS -o /dev/null -X POST -H "Cookie: ${guest_cookie}" http://127.0.0.1:8010/logout
unset guest_cookie
rm -f "${guest_headers}" "${guest_body}"
guest_headers=""
guest_body=""
if ss -ltn sport = :8010 | awk 'NR>1 {print $4}' | grep -vE '^(127\.0\.0\.1|\[::ffff:127\.0\.0\.1\]):8010$' | grep -q .; then
  echo "auth service is not bound to localhost only" >&2
  exit 1
fi

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
login_body=$(mktemp)
local_root_body=$(mktemp)
local_root_code=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  local_root_code=$(curl -k -sS --resolve whalpha.com:443:127.0.0.1 -o "${local_root_body}" -w '%{http_code}' https://whalpha.com/)
  if [[ "${local_root_code}" == "200" ]] && grep -q 'Quantitative Market Structure' "${local_root_body}"; then
    break
  fi
  sleep 1
done
[[ "${local_root_code}" == "200" ]] || { echo "local root login failed" >&2; exit 1; }
grep -q 'Quantitative Market Structure' "${local_root_body}" || { echo "local root login missing branded marker" >&2; exit 1; }
grep -q 'name="username"' "${local_root_body}" || { echo "local root login missing username field" >&2; exit 1; }
grep -q 'name="password"' "${local_root_body}" || { echo "local root login missing password field" >&2; exit 1; }
grep -q 'class="guest-submit"' "${local_root_body}" || { echo "local root login missing guest entry" >&2; exit 1; }
if grep -q 'New platform under development' "${local_root_body}"; then
  echo "local root route returned placeholder body" >&2
  exit 1
fi
public_code=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  public_code=$(curl -sS -H 'Cache-Control: no-cache' -o "${public_body}" -w '%{http_code}' https://whalpha.com/)
  if [[ "${public_code}" == "200" ]] && grep -q 'Quantitative Market Structure' "${public_body}"; then
    break
  fi
  sleep 1
done
[[ "${public_code}" == "200" ]] || { echo "public https failed" >&2; exit 1; }
grep -q 'WH Alpha' "${public_body}" || { echo "root login missing WH Alpha" >&2; exit 1; }
grep -q 'Quantitative Market Structure' "${public_body}" || { echo "root login missing branded marker" >&2; exit 1; }
grep -q 'name="username"' "${public_body}" || { echo "root login missing username field" >&2; exit 1; }
grep -q 'name="password"' "${public_body}" || { echo "root login missing password field" >&2; exit 1; }
grep -q 'class="guest-submit"' "${public_body}" || { echo "root login missing guest entry" >&2; exit 1; }
grep -q 'Sign In' "${public_body}" || { echo "root login missing sign-in button" >&2; exit 1; }
if grep -q 'New platform under development' "${public_body}"; then
  echo "root route returned placeholder body" >&2
  exit 1
fi
dashboard_code=$(curl -sS -o "${private_body}" -w '%{http_code}' https://whalpha.com/dashboard/)
[[ "${dashboard_code}" == "302" ]] || { echo "dashboard unauth status ${dashboard_code}" >&2; exit 1; }
login_headers=$(mktemp)
login_code=$(curl -sS -D "${login_headers}" -o "${login_body}" -w '%{http_code}' https://whalpha.com/login/)
[[ "${login_code}" == "302" ]] || { echo "login compatibility redirect status ${login_code}" >&2; exit 1; }
grep -Eqi '^Location: (https://whalpha\.com)?/\??' "${login_headers}" || { echo "login compatibility redirect did not target root" >&2; exit 1; }
rm -f "${login_headers}"
login_js_headers=$(mktemp)
login_css_headers=$(mktemp)
js_code=$(curl -sS -D "${login_js_headers}" -o /dev/null -w '%{http_code}' https://whalpha.com/login/login.js)
css_code=$(curl -sS -D "${login_css_headers}" -o /dev/null -w '%{http_code}' https://whalpha.com/login/login.css)
[[ "${js_code}" == "200" ]] || { echo "login JavaScript asset status ${js_code}" >&2; exit 1; }
[[ "${css_code}" == "200" ]] || { echo "login CSS asset status ${css_code}" >&2; exit 1; }
grep -Eiq '^Content-Type:.*(javascript|ecmascript)' "${login_js_headers}" || { echo "login JavaScript asset content type mismatch" >&2; exit 1; }
grep -Eiq '^Content-Type:.*text/css' "${login_css_headers}" || { echo "login CSS asset content type mismatch" >&2; exit 1; }
rm -f "${login_js_headers}" "${login_css_headers}"
public_login_headers=$(mktemp)
public_login_body=$(mktemp)
public_login_code=$(curl -sS -D "${public_login_headers}" -o "${public_login_body}" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Origin: https://whalpha.com' --data '{"username":"invalid-test-user","password":"invalid-test-password","next":"/dashboard/"}' https://whalpha.com/auth/login)
[[ "${public_login_code}" == "401" ]] || { echo "public invalid-login status ${public_login_code}" >&2; exit 1; }
grep -q '"error":"invalid_credentials"' "${public_login_body}" || { echo "public invalid-login response was not generic auth failure" >&2; exit 1; }
if grep -qi '^Set-Cookie:' "${public_login_headers}" || grep -q 'invalid-test-password' "${public_login_body}" || grep -q 'invalid-test-user' "${public_login_body}"; then
  echo "public invalid-login leaked credential material" >&2
  exit 1
fi
rm -f "${public_login_headers}" "${public_login_body}"
guest_cookie_jar=$(mktemp)
guest_body=$(mktemp)
guest_dashboard_body=$(mktemp)
guest_private_body=$(mktemp)
guest_candidate_body=$(mktemp)
guest_candidate_detail_body=$(mktemp)
guest_strategy_body=$(mktemp)
guest_code=$(curl -sS -c "${guest_cookie_jar}" -o "${guest_body}" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Origin: https://whalpha.com' --data '{"next":"/dashboard/?view=regime&lang=en"}' https://whalpha.com/auth/guest)
[[ "${guest_code}" == "200" ]] || { echo "public guest Session status ${guest_code}" >&2; exit 1; }
grep -q '"authenticated":true' "${guest_body}" || { echo "public guest Session response mismatch" >&2; exit 1; }
guest_dashboard_code=$(curl -sS -b "${guest_cookie_jar}" -o "${guest_dashboard_body}" -w '%{http_code}' https://whalpha.com/dashboard/)
[[ "${guest_dashboard_code}" == "200" ]] || { echo "guest Dashboard status ${guest_dashboard_code}" >&2; exit 1; }
grep -q '<div id="root"></div>' "${guest_dashboard_body}" || { echo "guest Dashboard shell mismatch" >&2; exit 1; }
guest_private_code=$(curl -sS -b "${guest_cookie_jar}" -o "${guest_private_body}" -w '%{http_code}' https://whalpha.com/private-data/v1/manifest.json)
[[ "${guest_private_code}" == "200" ]] || { echo "guest private-data status ${guest_private_code}" >&2; exit 1; }
grep -Eq '"snapshot_contract_version":"1\.(5|6|7|8|9)"' "${guest_private_body}" || { echo "guest private-data contract mismatch" >&2; exit 1; }
if grep -Eq '"snapshot_contract_version":"1\.(6|7|8|9)"' "${guest_private_body}"; then
  grep -q '"candidate_contract_version":"opportunity-candidate/1.1"' "${guest_private_body}" || { echo "guest Candidate manifest contract mismatch" >&2; exit 1; }
  guest_candidate_filename=opportunity-candidates.json
  if grep -Eq '"snapshot_contract_version":"1\.(8|9)"' "${guest_private_body}"; then
    guest_candidate_filename=opportunity-candidates-summary.json
  fi
  guest_candidate_code=$(curl -sS -b "${guest_cookie_jar}" -o "${guest_candidate_body}" -w '%{http_code}' "https://whalpha.com/private-data/v1/${guest_candidate_filename}")
  [[ "${guest_candidate_code}" == "200" ]] || { echo "guest Candidate data status ${guest_candidate_code}" >&2; exit 1; }
  grep -Eq '"contract_version":"(opportunity-candidate-snapshot/1\.(0|1)|opportunity-candidate-summary-snapshot/1\.0)"' "${guest_candidate_body}" || { echo "guest Candidate contract mismatch" >&2; exit 1; }
  grep -q '"underlying_stock_result_not_option_return":true' "${guest_candidate_body}" || { echo "guest Candidate decision boundary missing" >&2; exit 1; }
  if grep -Eq '"snapshot_contract_version":"1\.(7|8|9)"' "${guest_private_body}"; then
    grep -q '"entry_location_separate_from_leadership":true' "${guest_candidate_body}" || { echo "guest entry-geometry boundary missing" >&2; exit 1; }
    grep -q '"leadership_rank_preserved":true' "${guest_candidate_body}" || { echo "guest leadership-rank boundary missing" >&2; exit 1; }
  fi
  if grep -Eq '"snapshot_contract_version":"1\.(8|9)"' "${guest_private_body}"; then
    guest_detail_filename=$(python3 - "${guest_private_body}" <<'PY'
import json,sys
value=json.load(open(sys.argv[1],encoding='utf-8'))
files=value.get('candidate_detail_files') or []
if not files: raise SystemExit(1)
print(files[0])
PY
)
    guest_detail_code=$(curl -sS -b "${guest_cookie_jar}" -o "${guest_candidate_detail_body}" -w '%{http_code}' "https://whalpha.com/private-data/v1/${guest_detail_filename}")
    [[ "${guest_detail_code}" == "200" ]] || { echo "guest Candidate detail status ${guest_detail_code}" >&2; exit 1; }
    grep -q '"contract_version":"opportunity-candidate-detail-shard/1.0"' "${guest_candidate_detail_body}" || { echo "guest Candidate detail contract mismatch" >&2; exit 1; }
  fi
  if grep -q '"snapshot_contract_version":"1.9"' "${guest_private_body}"; then
    guest_strategy_code=$(curl -sS -b "${guest_cookie_jar}" -o "${guest_strategy_body}" -w '%{http_code}' "https://whalpha.com/private-data/v1/candidate-strategy-channels.json")
    [[ "${guest_strategy_code}" == "200" ]] || { echo "guest Candidate strategy-channel status ${guest_strategy_code}" >&2; exit 1; }
    python3 - "${guest_private_body}" "${guest_strategy_body}" <<'PY'
import json,sys
manifest=json.load(open(sys.argv[1],encoding='utf-8'))
strategy=json.load(open(sys.argv[2],encoding='utf-8'))
source=strategy.get('source',{})
if (manifest.get('candidate_strategy_file') != 'candidate-strategy-channels.json'
    or strategy.get('contract_version') != 'candidate-strategy-channel-product/1.0'
    or strategy.get('logical_fingerprint') != manifest.get('candidate_strategy_logical_fingerprint')
    or source.get('strategy_audit_logical_fingerprint') != manifest.get('candidate_strategy_audit_logical_fingerprint')
    or source.get('strategy_oracle_mismatch_count') != 0
    or source.get('strategy_input_permutation_match') is not True
    or strategy.get('cross_channel_score_comparison_prohibited') is not True
    or strategy.get('fixed_baseline_not_chronologically_validated') is not True
    or strategy.get('underlying_stock_result_not_option_return') is not True
    or strategy.get('guest_and_credential_capability_identical') is not True):
  raise SystemExit('guest Candidate strategy-channel binding is invalid')
PY
  fi
fi
guest_logout_code=$(curl -sS -b "${guest_cookie_jar}" -o /dev/null -w '%{http_code}' -X POST https://whalpha.com/auth/logout)
[[ "${guest_logout_code}" == "303" ]] || { echo "guest logout status ${guest_logout_code}" >&2; exit 1; }
rm -f "${guest_cookie_jar}" "${guest_body}" "${guest_dashboard_body}" "${guest_private_body}" "${guest_candidate_body}" "${guest_candidate_detail_body}" "${guest_strategy_body}"
guest_cookie_jar=""
guest_body=""
guest_dashboard_body=""
guest_private_body=""
guest_candidate_body=""
guest_candidate_detail_body=""
guest_strategy_body=""
private_code=$(curl -sS -o "${private_body}" -w '%{http_code}' https://whalpha.com/private-data/v1/manifest.json)
[[ "${private_code}" == "401" ]] || { echo "private-data unauth status ${private_code}" >&2; exit 1; }
if grep -q '"current_session_date"\|"release_id"\|"nodes"' "${private_body}"; then
  echo "private-data unauth response exposed private payload" >&2
  exit 1
fi
status_headers=$(mktemp)
status_body=$(mktemp)
status_code=$(curl -sS -D "${status_headers}" -o "${status_body}" -w '%{http_code}' https://whalpha.com/auth/status)
[[ "${status_code}" == "401" ]] || { echo "auth status unauth status ${status_code}" >&2; exit 1; }
grep -qi '^Cache-Control:.*no-store' "${status_headers}" || { echo "auth status missing no-store" >&2; exit 1; }
[[ ! -s "${status_body}" ]] || { echo "auth status returned unexpected body" >&2; exit 1; }
rm -f "${status_headers}" "${status_body}"
auth_internal_code=$(curl -sS -o /dev/null -w '%{http_code}' https://whalpha.com/auth/internal-verify)
[[ "${auth_internal_code}" == "404" ]] || { echo "internal verify exposed ${auth_internal_code}" >&2; exit 1; }
http_code=$(curl -sS -o /dev/null -w '%{http_code}' http://whalpha.com/)
[[ "${http_code}" == "301" || "${http_code}" == "308" ]] || { echo "http redirect status ${http_code}" >&2; exit 1; }
for path in /dashboard /dashboard/index.html /private-data /private-data/ /private-data/v1/manifest.json /private-data/%2e%2e/dashboard/index.html /.env /deployment-manifest.json /checksums.sha256; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' "https://whalpha.com${path}")
  case "${path}:${code}" in
    /dashboard:301|/dashboard:302|/dashboard/index.html:302|/private-data:401|/private-data/:401|/private-data/:403|/private-data/v1/manifest.json:401|/private-data/%2e%2e/dashboard/index.html:400|/private-data/%2e%2e/dashboard/index.html:401|/.env:403|/.env:404|/deployment-manifest.json:404|/checksums.sha256:404) ;;
    *) echo "unexpected bypass result ${path} ${code}" >&2; exit 1 ;;
  esac
done
dashboard_headers=$(mktemp)
private_headers=$(mktemp)
curl -sS -I https://whalpha.com/dashboard/ | tr -d '\r' >"${dashboard_headers}"
grep -qi '^Location: .*/?next=/dashboard/' "${dashboard_headers}" || { echo "dashboard redirect missing root login location" >&2; exit 1; }
curl -sS -I https://whalpha.com/private-data/v1/manifest.json | tr -d '\r' >"${private_headers}"
grep -qi '^Cache-Control:.*no-store' "${private_headers}" || { echo "private-data missing no-store header" >&2; exit 1; }
rm -f "${dashboard_headers}" "${private_headers}"
rm -f "${public_body}" "${private_body}" "${login_body}" "${local_root_body}"
systemctl is-active --quiet nginx
[[ "$(systemctl --failed --no-legend | wc -l)" == "0" ]]
if ss -ltn | awk '{print $4}' | grep -Eq ':(8000|8001)$'; then
  echo "unexpected private backend listener after deploy" >&2
  exit 1
fi
if ss -ltn sport = :8010 | awk 'NR>1 {print $4}' | grep -vE '^(127\.0\.0\.1|\[::ffff:127\.0\.0\.1\]):8010$' | grep -q .; then
  echo "auth service listener is not localhost-only after deploy" >&2
  exit 1
fi
(cd "${release_dir}" && sha256sum -c checksums.sha256 >/dev/null)
echo "apply=ok"
echo "deployment_status=deployed_pending_manual_authenticated_visual_verification"
trap - EXIT
rm -rf "${extract_dir}"
rm -f "${remote_tar}" "${remote_template}" "${remote_auth_service}"
REMOTE

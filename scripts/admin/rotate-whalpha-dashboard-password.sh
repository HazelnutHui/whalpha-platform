#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HOSTNAME="${WHALPHA_ROTATE_EXPECTED_HOSTNAME:-hui}"
AUTH_DIR="${WHALPHA_ROTATE_AUTH_DIR:-/etc/nginx/auth}"
AUTH_FILE="${AUTH_DIR}/whalpha-dashboard.htpasswd"
USERNAME="hui"
AUTH_SERVICE="whalpha-dashboard-auth.service"
NGINX_SERVICE="nginx.service"
TEST_MODE="${WHALPHA_ROTATE_TEST_MODE:-0}"
LISTENER_FILE="${WHALPHA_ROTATE_LISTENER_FILE:-}"
SLEEP_SECONDS="${WHALPHA_ROTATE_SLEEP_SECONDS:-1}"
LISTENER_WAIT_ATTEMPTS="${WHALPHA_ROTATE_LISTENER_WAIT_ATTEMPTS:-15}"
MIN_PASSWORD_LENGTH=10

usage() {
  cat <<'EOF'
Usage:
  sudo ./rotate-whalpha-dashboard-password.sh
  sudo ./rotate-whalpha-dashboard-password.sh --apply

Dry-run is the default. --apply prompts interactively for the new password.
Do not pass passwords as arguments, environment variables, files, or piped stdin.
EOF
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit "${2:-1}"
}

safe_stat() {
  stat -c '%n|owner=%U:%G|mode=%a|type=%F' "$1"
}

require_no_secret_inputs() {
  for name in PASSWORD PASS HTPASSWD HASH WHALPHA_PASSWORD WHALPHA_DASHBOARD_PASSWORD; do
    if [[ -n "${!name:-}" ]]; then
      fail "password-like environment variables are not accepted"
    fi
  done
}

require_target_host() {
  local host
  host="$(hostname)"
  [[ "$host" == "$EXPECTED_HOSTNAME" ]] || fail "must run on the approved OCI host"
}

require_root() {
  if [[ "${EUID}" -ne 0 && "$TEST_MODE" != "1" ]]; then
    fail "must be run as root, typically through sudo"
  fi
}

validate_environment() {
  require_target_host
  require_root
  [[ -d "$AUTH_DIR" ]] || fail "auth directory is missing"
  [[ -f "$AUTH_FILE" ]] || fail "auth file is missing"
  [[ ! -L "$AUTH_FILE" ]] || fail "auth file must not be a symlink"
  if [[ "$TEST_MODE" != "1" ]]; then
    [[ "$(stat -c '%U:%G' "$AUTH_FILE")" == "root:www-data" ]] || fail "auth file owner must be root:www-data"
    local mode
    mode="$(stat -c '%a' "$AUTH_FILE")"
    [[ "$mode" =~ ^[0-6]?[0-4]0$|^640$|^600$ ]] || fail "auth file mode must be 640 or stricter"
    systemctl list-unit-files "$AUTH_SERVICE" >/dev/null 2>&1 || fail "auth service unit is missing"
    systemctl list-unit-files "$NGINX_SERVICE" >/dev/null 2>&1 || fail "nginx service unit is missing"
  fi
}

listener_addresses_from_ss() {
  awk '
    $1 == "State" { next }
    $1 == "LISTEN" && NF >= 4 { print $4; next }
    NF >= 1 { print $1 }
  '
}

collect_listener_addresses() {
  if [[ -n "$LISTENER_FILE" ]]; then
    listener_addresses_from_ss <"$LISTENER_FILE"
    return
  fi
  ss -H -ltn sport = :8010 | listener_addresses_from_ss
}

listener_is_localhost_only() {
  local addresses
  mapfile -t addresses < <(collect_listener_addresses | sed '/^$/d')
  [[ "${#addresses[@]}" -eq 1 ]] || return 1
  [[ "${addresses[0]}" == "127.0.0.1:8010" ]]
}

wait_for_listener() {
  local attempt
  for ((attempt = 1; attempt <= LISTENER_WAIT_ATTEMPTS; attempt += 1)); do
    if listener_is_localhost_only; then
      return 0
    fi
    sleep "$SLEEP_SECONDS"
  done
  return 1
}

ensure_listener_or_fail() {
  wait_for_listener || fail "auth service must listen only on 127.0.0.1:8010"
}

service_is_active() {
  if [[ "$TEST_MODE" == "1" ]]; then
    return 0
  fi
  systemctl is-active --quiet "$1"
}

restart_auth_service() {
  if [[ "$TEST_MODE" == "1" ]]; then
    printf 'would_restart=%s\n' "$AUTH_SERVICE"
    return 0
  fi
  systemctl restart "$AUTH_SERVICE"
}

verify_services_ready() {
  service_is_active "$AUTH_SERVICE" || return 1
  wait_for_listener || return 1
  service_is_active "$NGINX_SERVICE" || return 1
  return 0
}

dry_run() {
  validate_environment
  printf 'dry_run=ok\n'
  safe_stat "$AUTH_FILE"
  printf 'username=%s\n' "$USERNAME"
  printf 'auth_service=%s\n' "$AUTH_SERVICE"
  printf 'nginx_service=%s\n' "$NGINX_SERVICE"
  printf 'apply_required_for_rotation=true\n'
}

read_passwords() {
  [[ -t 0 ]] || fail "--apply requires an interactive terminal"
  local first second
  read -r -s -p "New WH Alpha password: " first
  printf '\n'
  read -r -s -p "Confirm new WH Alpha password: " second
  printf '\n'
  [[ -n "$first" ]] || fail "empty passwords are not allowed"
  [[ "$first" == "$second" ]] || fail "password entries did not match"
  [[ "${#first}" -ge "$MIN_PASSWORD_LENGTH" ]] || fail "password must be at least 10 characters"
  ROTATE_PASSWORD="$first"
  unset first second
}

make_hash() {
  command -v openssl >/dev/null 2>&1 || fail "openssl is required"
  ROTATE_HASH="$(printf '%s\n' "$ROTATE_PASSWORD" | openssl passwd -6 -stdin)"
  [[ -n "$ROTATE_HASH" ]] || fail "password hash generation failed"
  unset ROTATE_PASSWORD
}

restore_backup() {
  local backup="$1"
  local restore_tmp
  [[ -f "$backup" ]] || return 1
  restore_tmp="$(mktemp "${AUTH_DIR}/.whalpha-dashboard.restore.XXXXXX")"
  if [[ "$TEST_MODE" == "1" ]]; then
    cp "$backup" "$restore_tmp"
  else
    install -m 640 -o root -g www-data "$backup" "$restore_tmp"
  fi
  chmod 640 "$restore_tmp"
  mv -f "$restore_tmp" "$AUTH_FILE"
  if [[ "$TEST_MODE" != "1" ]]; then
    chown root:www-data "$AUTH_FILE"
    chmod 640 "$AUTH_FILE"
  fi
  restart_auth_service || return 1
  verify_services_ready || return 1
  return 0
}

fail_after_replace() {
  local backup="$1"
  local reason="$2"
  printf 'rotation_failed=true\n' >&2
  printf 'failure_reason=%s\n' "$reason" >&2
  printf 'rollback_attempted=true\n' >&2
  if restore_backup "$backup"; then
    printf 'rollback_succeeded=true\n' >&2
    fail "$reason"
  fi
  printf 'rollback_failed=true\n' >&2
  fail "password rotation failed and rollback failed: $reason"
}

apply_rotation() {
  validate_environment
  read_passwords
  make_hash

  local timestamp backup tmp replaced
  replaced="false"
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="${AUTH_DIR}/whalpha-dashboard.htpasswd.backup-${timestamp}"
  tmp="$(mktemp "${AUTH_DIR}/.whalpha-dashboard.htpasswd.XXXXXX")"
  chmod 600 "$tmp"
  trap 'unset ROTATE_PASSWORD ROTATE_HASH; [[ -n "${tmp:-}" && -e "${tmp:-}" ]] && rm -f "$tmp"' EXIT

  if [[ "$TEST_MODE" == "1" ]]; then
    cp "$AUTH_FILE" "$backup"
    chmod 600 "$backup"
  else
    install -m 600 -o root -g root "$AUTH_FILE" "$backup"
  fi
  printf '%s:%s\n' "$USERNAME" "$ROTATE_HASH" >"$tmp"
  unset ROTATE_HASH
  if [[ "$TEST_MODE" != "1" ]]; then
    chown root:www-data "$tmp"
  fi
  chmod 640 "$tmp"
  [[ "$(awk -F: -v user="$USERNAME" 'NF >= 2 && $1 == user { count += 1 } END { print count + 0 }' "$tmp")" == "1" ]] || fail "new auth file validation failed"

  mv -f "$tmp" "$AUTH_FILE"
  tmp=""
  replaced="true"
  if ! restart_auth_service; then
    fail_after_replace "$backup" "auth service restart failed after rotation"
  fi
  if ! verify_services_ready; then
    fail_after_replace "$backup" "auth service readiness verification failed after rotation"
  fi
  printf 'password_rotation=completed\n'
  safe_stat "$AUTH_FILE"
  printf 'sessions_invalidated=true\n'
  printf 'auth_service=active\n'
  printf 'listener=127.0.0.1:8010\n'
  [[ "$replaced" == "true" ]]
}

main() {
  require_no_secret_inputs
  case "${1:-}" in
    "")
      dry_run
      ;;
    "--help")
      usage
      ;;
    "--apply")
      [[ "$#" -eq 1 ]] || fail "unexpected arguments" 2
      apply_rotation
      ;;
    *)
      fail "unknown argument" 2
      ;;
  esac
}

if [[ "${WHALPHA_ROTATE_SOURCE_ONLY:-0}" != "1" ]]; then
  main "$@"
fi

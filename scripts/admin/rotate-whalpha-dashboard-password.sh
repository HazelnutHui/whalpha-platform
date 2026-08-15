#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
EXPECTED_HOSTNAME="${WHALPHA_ROTATE_EXPECTED_HOSTNAME:-hui}"
AUTH_DIR="${WHALPHA_ROTATE_AUTH_DIR:-/etc/nginx/auth}"
AUTH_FILE="${AUTH_DIR}/whalpha-dashboard.htpasswd"
USERNAME="hui"
AUTH_SERVICE="whalpha-dashboard-auth.service"
NGINX_SERVICE="nginx.service"
TEST_MODE="${WHALPHA_ROTATE_TEST_MODE:-0}"

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
  [[ "${#first}" -ge 16 ]] || fail "password must be at least 16 characters"
  ROTATE_PASSWORD="$first"
  unset first second
}

make_hash() {
  command -v openssl >/dev/null 2>&1 || fail "openssl is required"
  ROTATE_HASH="$(printf '%s\n' "$ROTATE_PASSWORD" | openssl passwd -6 -stdin)"
  [[ -n "$ROTATE_HASH" ]] || fail "password hash generation failed"
  unset ROTATE_PASSWORD
}

verify_listener() {
  if [[ "$TEST_MODE" == "1" ]]; then
    return
  fi
  ss -ltn sport = :8010 | awk 'NR > 1 { print $4 }' | grep -qx '127.0.0.1:8010' || fail "auth service must listen only on 127.0.0.1:8010"
  if ss -ltn sport = :8010 | awk 'NR > 1 { print $4 }' | grep -vq '127.0.0.1:8010'; then
    fail "auth service has an unexpected listener"
  fi
}

restart_services() {
  if [[ "$TEST_MODE" == "1" ]]; then
    printf 'would_restart=%s\n' "$AUTH_SERVICE"
    return
  fi
  systemctl restart "$AUTH_SERVICE"
  systemctl is-active --quiet "$AUTH_SERVICE" || fail "auth service did not become active"
  verify_listener
  systemctl is-active --quiet "$NGINX_SERVICE" || fail "nginx is not active"
}

restore_backup() {
  local backup="$1"
  if [[ -f "$backup" ]]; then
    install -m 640 -o root -g www-data "$backup" "$AUTH_FILE"
    restart_services || true
    printf 'restore_attempted=true\n' >&2
  fi
}

apply_rotation() {
  validate_environment
  read_passwords
  make_hash

  local timestamp backup tmp
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

  if ! mv -f "$tmp" "$AUTH_FILE"; then
    restore_backup "$backup"
    fail "auth file replacement failed"
  fi
  tmp=""
  if ! restart_services; then
    restore_backup "$backup"
    fail "auth service restart failed after rotation"
  fi
  printf 'rotation=completed\n'
  safe_stat "$AUTH_FILE"
  printf 'sessions_invalidated=true\n'
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

main "$@"

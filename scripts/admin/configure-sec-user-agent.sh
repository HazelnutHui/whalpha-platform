#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HOSTNAME="dell5820"
EXPECTED_USER="hui"
CONFIG_DIR="/home/hui/.config/trading-intelligence-platform"
CONFIG_FILE="${CONFIG_DIR}/sec.env"
CONFIG_KEY="TIP_SEC_USER_AGENT"

usage() {
  cat <<'EOF'
Usage:
  scripts/admin/configure-sec-user-agent.sh
  scripts/admin/configure-sec-user-agent.sh --apply

Dry-run is the default. --apply reads the private SEC User-Agent from an
interactive terminal and stores it without printing it.
EOF
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit "${2:-1}"
}

require_identity() {
  [[ "$(hostname)" == "$EXPECTED_HOSTNAME" ]] || fail "must run on the approved workstation"
  [[ "$(id -un)" == "$EXPECTED_USER" ]] || fail "must run as the approved workstation user"
  [[ "$(id -u)" -ne 0 ]] || fail "must not run as root"
}

require_no_injected_value() {
  [[ -z "${TIP_SEC_USER_AGENT:-}" ]] || fail "SEC User-Agent environment input is not accepted"
}

dry_run() {
  require_identity
  require_no_injected_value
  printf 'mode=dry-run\n'
  printf 'path=%s\n' "$CONFIG_FILE"
  printf 'configured=%s\n' "$([[ -f "$CONFIG_FILE" && ! -L "$CONFIG_FILE" ]] && printf true || printf false)"
  printf 'apply_required=true\n'
}

validate_value() {
  local value="$1"
  [[ -n "$value" ]] || fail "SEC User-Agent must not be empty"
  [[ "${#value}" -ge 10 && "${#value}" -le 256 ]] || fail "SEC User-Agent format is invalid"
  [[ "$value" == *"trading-intelligence-platform"* ]] || fail "SEC User-Agent must contain the project identifier"
  [[ "$value" =~ [[:alnum:]._%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,} ]] || fail "SEC User-Agent must contain a contact email"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || fail "SEC User-Agent format is invalid"
}

apply_config() {
  require_identity
  require_no_injected_value
  [[ -t 0 && -t 1 ]] || fail "--apply requires an interactive terminal"

  local value temporary
  IFS= read -r -s -p "SEC User-Agent: " value
  printf '\n'
  validate_value "$value"

  umask 077
  mkdir -p "$CONFIG_DIR"
  chmod 700 "$CONFIG_DIR"
  [[ ! -L "$CONFIG_DIR" ]] || fail "configuration directory must not be a symlink"
  if [[ -e "$CONFIG_FILE" ]]; then
    [[ -f "$CONFIG_FILE" && ! -L "$CONFIG_FILE" ]] || fail "existing configuration must be a regular non-symlink file"
    [[ "$(stat -c '%U' "$CONFIG_FILE")" == "$EXPECTED_USER" ]] || fail "existing configuration owner is invalid"
  fi
  temporary="$(mktemp "${CONFIG_DIR}/.sec.env.tmp.XXXXXX")"
  trap 'unset value; [[ -n "${temporary:-}" && -e "${temporary:-}" ]] && rm -f "$temporary"' EXIT
  printf '%s=%s\n' "$CONFIG_KEY" "$value" >"$temporary"
  unset value
  chmod 600 "$temporary"
  mv -f "$temporary" "$CONFIG_FILE"
  temporary=""
  [[ "$(stat -c '%U' "$CONFIG_FILE")" == "$EXPECTED_USER" ]] || fail "configured file owner validation failed"
  [[ "$(stat -c '%a' "$CONFIG_FILE")" == "600" ]] || fail "configured file mode validation failed"
  printf 'path=%s\n' "$CONFIG_FILE"
  printf 'owner=%s\n' "$EXPECTED_USER"
  printf 'mode=600\n'
  printf 'configured=true\n'
}

main() {
  case "${1:-}" in
    "")
      [[ "$#" -eq 0 ]] || fail "unexpected arguments" 2
      dry_run
      ;;
    "--help")
      [[ "$#" -eq 1 ]] || fail "unexpected arguments" 2
      usage
      ;;
    "--apply")
      [[ "$#" -eq 1 ]] || fail "unexpected arguments" 2
      apply_config
      ;;
    *) fail "unknown argument" 2 ;;
  esac
}

main "$@"

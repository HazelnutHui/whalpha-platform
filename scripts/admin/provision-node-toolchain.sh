#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HOST="dell5820"
EXPECTED_UBUNTU_ID="ubuntu"
EXPECTED_UBUNTU_VERSION_PREFIX="24.04"
EXPECTED_ARCH="amd64"
EXPECTED_NODE_MAJOR="24"
NODESOURCE_KEY_URL="https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key"
KEYRING_PATH="/etc/apt/keyrings/nodesource-node24.gpg"
SOURCE_LIST_PATH="/etc/apt/sources.list.d/nodesource-node24.list"
SOURCE_LIST_CONTENT="deb [arch=amd64 signed-by=/etc/apt/keyrings/nodesource-node24.gpg] https://deb.nodesource.com/node_24.x nodistro main"
MODE="dry-run"
TEMP_FILES=()

usage() {
  cat <<USAGE
Usage: $0 [--apply]

Provision Node.js 24 LTS from the NodeSource node_24.x DEB repository.

Default mode is dry-run. Dry-run validates host, OS, architecture, tools,
existing Node/npm state, and planned repository files without modifying the
system, running apt-get update, or installing packages.

Options:
  --apply   Install the Node.js 24 system toolchain. Must be run as root.
  --help    Show this help.
USAGE
}

log() {
  printf '\n==> %s\n' "$*"
}

info() {
  printf '    %s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

register_temp() {
  TEMP_FILES+=("$1")
}

cleanup_temp_files() {
  local file
  for file in "${TEMP_FILES[@]:-}"; do
    if [[ -n "$file" && -e "$file" ]]; then
      case "$file" in
        /tmp/tip-node-toolchain.*|/etc/apt/keyrings/.nodesource-node24.*|/etc/apt/sources.list.d/.nodesource-node24.*)
          if [[ -d "$file" ]]; then
            rm -f -- "$file/nodesource-repo.gpg.key" "$file/nodesource-node24.gpg"
            rmdir -- "$file" 2>/dev/null || true
          else
            rm -f -- "$file"
          fi
          ;;
      esac
    fi
  done
}
trap cleanup_temp_files EXIT

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_host() {
  local host
  host=$(hostname)
  [[ "$host" == "$EXPECTED_HOST" ]] || fail "expected hostname $EXPECTED_HOST, got $host"
}

require_os() {
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "$EXPECTED_UBUNTU_ID" ]] || fail "expected Ubuntu, got ${ID:-unknown}"
  [[ "${VERSION_ID:-}" == "$EXPECTED_UBUNTU_VERSION_PREFIX"* ]] || fail "expected Ubuntu 24.04 series, got ${VERSION_ID:-unknown}"
}

require_arch() {
  local arch
  arch=$(dpkg --print-architecture)
  [[ "$arch" == "$EXPECTED_ARCH" ]] || fail "expected architecture $EXPECTED_ARCH, got $arch"
}

require_root_for_apply() {
  [[ "${EUID}" -eq 0 ]] || fail "--apply must be run as root; use sudo $0 --apply"
}

require_commands() {
  local commands=(apt-get curl gpg dpkg dpkg-query apt-cache awk grep sed install mktemp mv chmod chown readlink)
  local cmd
  for cmd in "${commands[@]}"; do
    require_command "$cmd"
  done
}

check_dpkg_state() {
  local audit_output
  audit_output=$(dpkg --audit)
  [[ -z "$audit_output" ]] || fail "dpkg reports unfinished package state; resolve manually before continuing"
}

node_major() {
  node --version | sed -E 's/^v([0-9]+).*/\1/'
}

check_existing_node() {
  local node_path npm_path major resolved owner policy
  node_path=$(command -v node || true)
  npm_path=$(command -v npm || true)

  if [[ -n "$node_path" || -n "$npm_path" ]]; then
    [[ -n "$node_path" && -n "$npm_path" ]] || fail "partial Node/npm installation detected; inspect manually"
    major=$(node_major)
    resolved=$(readlink -f "$node_path")
    owner=$(dpkg-query -S "$resolved" 2>/dev/null || true)
    policy=$(apt-cache policy nodejs || true)
    [[ "$major" == "$EXPECTED_NODE_MAJOR" ]] || fail "existing node major version is $major, expected $EXPECTED_NODE_MAJOR; not overwriting"
    [[ "$owner" == nodejs:* || "$owner" == *': '* ]] || fail "existing node path is not owned by a dpkg package: $resolved"
    [[ "$policy" == *"deb.nodesource.com/node_24.x"* || "$policy" == *"Installed:"* ]] || fail "existing nodejs package source is unclear; inspect apt-cache policy manually"
    info "Existing Node.js 24 installation detected; apply can skip package installation if repository state is valid."
  fi
}

check_conflicting_nodesource_files() {
  local file base found_conflict=0
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    base=$(basename "$file")
    case "$file" in
      "$SOURCE_LIST_PATH"|"$KEYRING_PATH") ;;
      *)
        printf 'Found possible conflicting NodeSource/Node file: %s\n' "$file" >&2
        found_conflict=1
        ;;
    esac
  done < <(find /etc/apt/sources.list.d /etc/apt/keyrings /usr/share/keyrings -maxdepth 1 -type f \( -iname '*nodesource*' -o -iname '*node_*.list' -o -iname '*node*.gpg' \) 2>/dev/null || true)
  [[ "$found_conflict" -eq 0 ]] || fail "conflicting NodeSource/Node repository or keyring file exists; inspect manually"
}

check_target_file_state() {
  if [[ -e "$SOURCE_LIST_PATH" ]]; then
    if ! grep -Fxq "$SOURCE_LIST_CONTENT" "$SOURCE_LIST_PATH"; then
      fail "$SOURCE_LIST_PATH exists but does not contain the expected NodeSource node_24.x entry"
    fi
    info "Expected source list already exists: $SOURCE_LIST_PATH"
  fi

  if [[ -e "$KEYRING_PATH" ]]; then
    if [[ ! -s "$KEYRING_PATH" ]]; then
      fail "$KEYRING_PATH exists but is empty"
    fi
    if ! gpg --show-keys "$KEYRING_PATH" >/dev/null 2>&1; then
      fail "$KEYRING_PATH exists but is not a readable GPG keyring"
    fi
    if [[ ! -e "$SOURCE_LIST_PATH" ]]; then
      fail "$KEYRING_PATH exists without the expected source list; inspect manually"
    fi
    info "Readable NodeSource keyring already exists: $KEYRING_PATH"
  fi
}

preflight() {
  log "Preflight"
  require_host
  require_os
  require_arch
  require_commands
  check_dpkg_state
  check_existing_node
  check_conflicting_nodesource_files
  check_target_file_state
  info "Host, OS, architecture, dpkg state, and existing Node/npm state are acceptable."
}

download_and_install_keyring() {
  local temp_dir key_tmp keyring_tmp
  temp_dir=$(mktemp -d /tmp/tip-node-toolchain.keyring.XXXXXX)
  register_temp "$temp_dir"
  key_tmp="${temp_dir}/nodesource-repo.gpg.key"
  keyring_tmp="${temp_dir}/nodesource-node24.gpg"

  curl --fail --show-error --location --output "$key_tmp" "$NODESOURCE_KEY_URL"
  [[ -s "$key_tmp" ]] || fail "downloaded NodeSource key is empty"
  gpg --show-keys "$key_tmp" >/dev/null 2>&1 || fail "downloaded NodeSource key is not a valid GPG public key"
  [[ ! -e "$keyring_tmp" ]] || fail "internal keyring output path unexpectedly exists: $keyring_tmp"
  gpg --batch --yes --dearmor --output "$keyring_tmp" "$key_tmp"
  [[ -s "$keyring_tmp" ]] || fail "dearmored NodeSource keyring is empty"
  chown root:root "$keyring_tmp"
  chmod 0644 "$keyring_tmp"
  mv "$keyring_tmp" "$KEYRING_PATH"
  info "Installed dedicated NodeSource keyring: $KEYRING_PATH"
}

install_source_list() {
  local source_tmp
  source_tmp=$(mktemp /etc/apt/sources.list.d/.nodesource-node24.list.XXXXXX)
  register_temp "$source_tmp"
  printf '%s\n' "$SOURCE_LIST_CONTENT" > "$source_tmp"
  chown root:root "$source_tmp"
  chmod 0644 "$source_tmp"
  mv "$source_tmp" "$SOURCE_LIST_PATH"
  info "Installed NodeSource source list: $SOURCE_LIST_PATH"
}

verify_node_installation() {
  local node_version npm_version node_path npm_path node_major_value package_status
  node_path=$(command -v node || true)
  npm_path=$(command -v npm || true)
  [[ -n "$node_path" ]] || fail "node command not found after installation"
  [[ -n "$npm_path" ]] || fail "npm command not found after installation"
  node_version=$(node --version)
  npm_version=$(npm --version)
  node_major_value=$(node_major)
  [[ "$node_major_value" == "$EXPECTED_NODE_MAJOR" ]] || fail "installed node major $node_major_value, expected $EXPECTED_NODE_MAJOR"
  package_status=$(dpkg-query -W -f='${Package}|${Version}|${Architecture}|${Status}\n' nodejs)
  [[ "$package_status" == nodejs*"|amd64|install ok installed" ]] || fail "unexpected nodejs package status: $package_status"
  info "node=$node_version"
  info "npm=$npm_version"
  info "node_path=$(readlink -f "$node_path")"
  info "npm_path=$(readlink -f "$npm_path")"
  info "package=$package_status"
}

apply_changes() {
  require_root_for_apply
  preflight

  log "Install NodeSource repository"
  install -d -o root -g root -m 0755 /etc/apt/keyrings
  if [[ ! -e "$KEYRING_PATH" ]]; then
    download_and_install_keyring
  else
    info "Keeping existing expected keyring: $KEYRING_PATH"
  fi
  if [[ ! -e "$SOURCE_LIST_PATH" ]]; then
    install_source_list
  else
    info "Keeping existing expected source list: $SOURCE_LIST_PATH"
  fi

  log "Install nodejs package"
  apt-get update
  apt-get install -y nodejs

  log "Verify Node.js toolchain"
  verify_node_installation
  apt-cache policy nodejs
}

dry_run() {
  preflight
  log "Dry-run plan"
  info "Would install dedicated keyring: $KEYRING_PATH"
  info "Would install source list: $SOURCE_LIST_PATH"
  info "Repository entry: $SOURCE_LIST_CONTENT"
  info "Would run: apt-get update"
  info "Would run: apt-get install -y nodejs"
  info "Would verify node major version $EXPECTED_NODE_MAJOR and npm availability"
  info "No system changes were made."
}

main() {
  if (( $# == 0 )); then
    MODE="dry-run"
  elif (( $# == 1 )); then
    case "$1" in
      --apply) MODE="apply" ;;
      --help) usage; exit 0 ;;
      *) printf 'ERROR: invalid argument: %s. Use --help for usage.\n' "$1" >&2; exit 2 ;;
    esac
  else
    printf 'ERROR: invalid arguments. Use --help for usage.\n' >&2
    exit 2
  fi

  if [[ "$MODE" == "apply" ]]; then
    apply_changes
  else
    dry_run
  fi
}

main "$@"

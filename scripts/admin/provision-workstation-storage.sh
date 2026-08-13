#!/usr/bin/env bash
set -Eeuo pipefail

EXPECTED_HOST="dell5820"
EXPECTED_PV="/dev/nvme0n1p3"
EXPECTED_VG="ubuntu-vg"
ROOT_LV="/dev/ubuntu-vg/ubuntu-lv"
DATA_LV="/dev/ubuntu-vg/trading-data"
DATA_LV_NAME="trading-data"
DATA_MOUNT="/data"
PROJECT_DATA="/data/trading-intelligence-platform"
PROJECT_REPO="/home/hui/projects/trading-intelligence-platform"
DATA_LABEL="TIP_DATA"
GIB_BYTES=$((1024 * 1024 * 1024))
ROOT_INITIAL_BYTES=$((100 * GIB_BYTES))
ROOT_FINAL_BYTES=$((150 * GIB_BYTES))
ROOT_GROWTH_BYTES=$((50 * GIB_BYTES))
DATA_SIZE_BYTES=$((700 * GIB_BYTES))
RESERVED_VG_FREE_AFTER_BYTES=$((100 * GIB_BYTES))
REQUIRED_VG_FREE_BEFORE_BYTES=$((ROOT_GROWTH_BYTES + DATA_SIZE_BYTES + RESERVED_VG_FREE_AFTER_BYTES))
MIN_ROOT_FREE_BYTES=$((1 * GIB_BYTES))
export LC_ALL=C

MODE="dry-run"
CURRENT_PHASE="startup"
TEMP_FILES=()

usage() {
  cat <<USAGE
Usage: $0 [--apply]

Prepare workstation storage for Trading Intelligence Platform.

Default mode is dry-run. Dry-run prints the proposed plan and performs only
non-mutating checks that do not require sudo. It does not create LVM metadata
backups and does not modify disks, filesystems, /data, or /etc/fstab.

Options:
  --apply   Execute the approved storage changes. Must be run as root.
  --help    Show this help.

Approved target layout:
  root LV:      /dev/ubuntu-vg/ubuntu-lv -> 150G
  data LV:      /dev/ubuntu-vg/trading-data -> 700G
  data fs:      ext4, label TIP_DATA, 1% reserved blocks
  mountpoint:   /data
  project data: /data/trading-intelligence-platform
USAGE
}

log() {
  printf '\n==> %s\n' "$*"
}

info() {
  printf '    %s\n' "$*"
}

fail() {
  printf 'ERROR [%s]: %s\n' "$CURRENT_PHASE" "$*" >&2
  exit 1
}

on_error() {
  local exit_code=$?
  printf 'ERROR [%s]: command failed near line %s with exit code %s. No automatic LVM rollback was attempted.\n' \
    "$CURRENT_PHASE" "${BASH_LINENO[0]}" "$exit_code" >&2
}

register_temp_file() {
  TEMP_FILES+=("$1")
}

cleanup_temp_files() {
  local file
  for file in "${TEMP_FILES[@]:-}"; do
    if [[ -n "$file" && "$file" == /etc/fstab.tip-storage.* && -e "$file" ]]; then
      rm -f -- "$file"
    fi
  done
}
trap on_error ERR
trap cleanup_temp_files EXIT

trim() {
  awk '{$1=$1; print}'
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

lvm_bytes() {
  awk '{gsub(/[^0-9.]/, "", $1); printf "%.0f\n", $1}'
}

format_gib() {
  awk -v bytes="$1" 'BEGIN { printf "%.2f GiB", bytes / 1024 / 1024 / 1024 }'
}

single_value() {
  "$@" | trim
}

count_nonempty_lines() {
  awk 'NF {count++} END {print count + 0}'
}

require_host() {
  local host
  host=$(hostname)
  [[ "$host" == "$EXPECTED_HOST" ]] || fail "expected hostname $EXPECTED_HOST, got $host"
}

require_root_for_apply() {
  [[ "${EUID}" -eq 0 ]] || fail "--apply must be run as root; use sudo $0 --apply"
}

require_hui_identity() {
  getent passwd hui >/dev/null || fail "user hui does not exist"
  getent group hui >/dev/null || fail "group hui does not exist"
}

require_commands() {
  local commands=(
    pvs vgs lvs lvextend lvcreate mkfs.ext4 blkid findmnt mount install resize2fs
    vgcfgbackup df awk grep sed stat readlink chmod chown mv cp date mkdir
  )
  for cmd in "${commands[@]}"; do
    require_command "$cmd"
  done
}

fstab_has_data_reference() {
  awk '$2 == "/data" {found=1} END {exit found ? 0 : 1}' /etc/fstab && return 0
  grep -Eq 'TIP_DATA|trading-data|/dev/ubuntu-vg/trading-data|/dev/mapper/ubuntu--vg-trading--data' /etc/fstab
}

preflight_apply() {
  CURRENT_PHASE="preflight"
  log "Preflight verification"
  require_host
  require_root_for_apply
  require_hui_identity
  require_commands

  mapfile -t pv_lines < <(pvs --noheadings -o pv_name,vg_name | trim)
  [[ "${#pv_lines[@]}" -eq 1 ]] || fail "expected exactly one PV, found ${#pv_lines[@]}"
  [[ "${pv_lines[0]}" == "$EXPECTED_PV $EXPECTED_VG" ]] || fail "unexpected PV/VG: ${pv_lines[0]}"

  mapfile -t vg_names < <(vgs --noheadings -o vg_name | trim)
  [[ "${#vg_names[@]}" -eq 1 ]] || fail "expected exactly one VG, found ${#vg_names[@]}"
  [[ "${vg_names[0]}" == "$EXPECTED_VG" ]] || fail "unexpected VG: ${vg_names[0]}"

  local lv_count lv_name root_size_bytes root_segtype root_attr root_origin root_pool root_mount root_fs snap_count vg_free_bytes root_avail
  lv_count=$(lvs --noheadings -o lv_name "$EXPECTED_VG" | count_nonempty_lines)
  [[ "$lv_count" == "1" ]] || fail "expected one LV in $EXPECTED_VG before apply, found $lv_count"
  lv_name=$(single_value lvs --noheadings -o lv_name "$ROOT_LV")
  [[ "$lv_name" == "ubuntu-lv" ]] || fail "unexpected root LV name: $lv_name"

  root_size_bytes=$(lvs --noheadings --units b --nosuffix -o lv_size "$ROOT_LV" | lvm_bytes)
  [[ "$root_size_bytes" == "$ROOT_INITIAL_BYTES" ]] || fail "root LV must be exactly 100.00G before apply; got ${root_size_bytes} bytes"

  root_segtype=$(single_value lvs --noheadings -o segtype "$ROOT_LV")
  [[ "$root_segtype" == "linear" ]] || fail "root LV segtype must be linear; got $root_segtype"
  root_attr=$(single_value lvs --noheadings -o lv_attr "$ROOT_LV")
  [[ "${root_attr:0:1}" == "-" ]] || fail "root LV must be a normal linear LV, attr=$root_attr"
  [[ "${root_attr:4:1}" == "a" ]] || fail "root LV must be active, attr=$root_attr"
  root_origin=$(single_value lvs --noheadings -o origin "$ROOT_LV")
  root_pool=$(single_value lvs --noheadings -o pool_lv "$ROOT_LV")
  [[ -z "$root_origin" ]] || fail "root LV unexpectedly has origin: $root_origin"
  [[ -z "$root_pool" ]] || fail "root LV unexpectedly uses pool: $root_pool"

  root_fs=$(findmnt -n -o FSTYPE --target /)
  [[ "$root_fs" == "ext4" ]] || fail "root filesystem must be ext4; got $root_fs"
  root_mount=$(findmnt -n -o SOURCE --target /)
  [[ "$(readlink -f "$root_mount")" == "$(readlink -f "$ROOT_LV")" ]] || fail "root LV is not mounted at /; source=$root_mount"

  snap_count=$(single_value vgs --noheadings -o snap_count "$EXPECTED_VG")
  [[ "$snap_count" == "0" ]] || fail "VG snapshot count must be 0; got $snap_count"

  vg_free_bytes=$(vgs --noheadings --units b --nosuffix -o vg_free "$EXPECTED_VG" | lvm_bytes)
  (( vg_free_bytes >= REQUIRED_VG_FREE_BEFORE_BYTES )) || fail "VG free ${vg_free_bytes} bytes ($(format_gib "$vg_free_bytes")) is below required preflight minimum ${REQUIRED_VG_FREE_BEFORE_BYTES} bytes ($(format_gib "$REQUIRED_VG_FREE_BEFORE_BYTES"))"

  [[ ! -e "$DATA_LV" ]] || fail "$DATA_LV already exists"
  if lvs --noheadings -o lv_name "$EXPECTED_VG" | trim | grep -Fxq "$DATA_LV_NAME"; then
    fail "LV $DATA_LV_NAME already exists"
  fi

  [[ ! -e "$DATA_MOUNT" ]] || fail "$DATA_MOUNT already exists; refusing to continue"
  [[ ! -L "$DATA_MOUNT" ]] || fail "$DATA_MOUNT is a symlink"
  if findmnt --mountpoint "$DATA_MOUNT" >/dev/null 2>&1; then
    fail "$DATA_MOUNT is already a mountpoint"
  fi

  if fstab_has_data_reference; then
    fail "/etc/fstab already contains a /data, TIP_DATA, or trading-data reference"
  fi

  if ! findmnt --verify --verbose; then
    fail "findmnt fstab verification reported errors"
  fi

  [[ -d "$PROJECT_REPO" ]] || fail "project repository missing: $PROJECT_REPO"
  root_avail=$(df -B1 --output=avail / | awk 'NR==2 {print $1}')
  (( root_avail >= MIN_ROOT_FREE_BYTES )) || fail "root filesystem has less than 1GiB available"

  info "Preflight passed. VG free before apply: ${vg_free_bytes} bytes ($(format_gib "$vg_free_bytes"))."
  info "Required VG free before apply: ${REQUIRED_VG_FREE_BEFORE_BYTES} bytes ($(format_gib "$REQUIRED_VG_FREE_BEFORE_BYTES"))."
}

verify_root_after_resize() {
  CURRENT_PHASE="verify-root-after-resize"
  local root_size_bytes fs_size_bytes source
  root_size_bytes=$(lvs --noheadings --units b --nosuffix -o lv_size "$ROOT_LV" | lvm_bytes)
  [[ "$root_size_bytes" == "$ROOT_FINAL_BYTES" ]] || fail "root LV is not 150G after extension; got ${root_size_bytes} bytes"
  fs_size_bytes=$(df -B1 --output=size / | awk 'NR==2 {print $1}')
  (( fs_size_bytes > ROOT_INITIAL_BYTES )) || fail "root filesystem size did not grow; df size=${fs_size_bytes} bytes"
  source=$(findmnt -n -o SOURCE --target /)
  [[ "$(readlink -f "$source")" == "$(readlink -f "$ROOT_LV")" ]] || fail "/ is not mounted from $ROOT_LV after resize"
  local write_probe
  write_probe=$(mktemp /.tip-root-write-test.XXXXXX)
  rm -f "$write_probe"
}

verify_new_data_lv_empty() {
  CURRENT_PHASE="verify-new-data-lv"
  local data_size_bytes data_segtype data_attr
  [[ -e "$DATA_LV" ]] || fail "$DATA_LV was not created"
  data_size_bytes=$(lvs --noheadings --units b --nosuffix -o lv_size "$DATA_LV" | lvm_bytes)
  [[ "$data_size_bytes" == "$DATA_SIZE_BYTES" ]] || fail "data LV is not 700G; got ${data_size_bytes} bytes"
  data_segtype=$(single_value lvs --noheadings -o segtype "$DATA_LV")
  [[ "$data_segtype" == "linear" ]] || fail "data LV segtype must be linear; got $data_segtype"
  data_attr=$(single_value lvs --noheadings -o lv_attr "$DATA_LV")
  [[ "${data_attr:0:1}" == "-" ]] || fail "data LV is not a normal LV, attr=$data_attr"
  if blkid "$DATA_LV" >/dev/null 2>&1; then
    fail "$DATA_LV already has a filesystem signature; refusing to format"
  fi
}

verify_data_filesystem() {
  CURRENT_PHASE="verify-data-filesystem"
  local fs_type fs_label fs_uuid
  fs_type=$(blkid -s TYPE -o value "$DATA_LV")
  fs_label=$(blkid -s LABEL -o value "$DATA_LV")
  fs_uuid=$(blkid -s UUID -o value "$DATA_LV")
  [[ "$fs_type" == "ext4" ]] || fail "data LV TYPE must be ext4; got $fs_type"
  [[ "$fs_label" == "$DATA_LABEL" ]] || fail "data LV LABEL must be $DATA_LABEL; got $fs_label"
  [[ -n "$fs_uuid" ]] || fail "data LV UUID is empty"
  printf '%s\n' "$fs_uuid"
}

update_fstab() {
  CURRENT_PHASE="update-fstab"
  local data_uuid="$1"
  local backup tmp restore_tmp mode
  backup="/etc/fstab.tip-storage.$(date -u +%Y%m%dT%H%M%SZ).bak"
  tmp=$(mktemp /etc/fstab.tip-storage.XXXXXX)
  register_temp_file "$tmp"
  restore_tmp=""
  mode=$(stat -c '%a' /etc/fstab)
  cp /etc/fstab "$backup"
  chmod 600 "$backup"
  cp /etc/fstab "$tmp"
  printf 'UUID=%s %s ext4 defaults,nodev,nosuid 0 2\n' "$data_uuid" "$DATA_MOUNT" >> "$tmp"
  chown root:root "$tmp"
  chmod "$mode" "$tmp"
  mv "$tmp" /etc/fstab
  tmp=""
  chown root:root /etc/fstab
  chmod "$mode" /etc/fstab
  info "fstab_backup=$backup"
  if ! findmnt --verify --verbose; then
    restore_tmp=$(mktemp /etc/fstab.tip-storage.restore.XXXXXX)
    register_temp_file "$restore_tmp"
    cp "$backup" "$restore_tmp"
    chown root:root "$restore_tmp"
    chmod "$mode" "$restore_tmp"
    mv "$restore_tmp" /etc/fstab
    restore_tmp=""
    chown root:root /etc/fstab
    chmod "$mode" /etc/fstab
    if findmnt --verify --verbose; then
      fail "new fstab failed verification; restored atomically from $backup"
    fi
    printf 'CRITICAL [%s]: restored fstab from %s, but findmnt verification still fails. Inspect /etc/fstab manually.\n' "$CURRENT_PHASE" "$backup" >&2
    exit 1
  fi
  rm -f -- "$tmp" "$restore_tmp"
}

verify_data_mount() {
  CURRENT_PHASE="verify-data-mount"
  local expected_uuid="$1"
  local source source_uuid fstype options
  source=$(findmnt -n -o SOURCE --target "$DATA_MOUNT")
  source_uuid=$(blkid -s UUID -o value "$source")
  fstype=$(findmnt -n -o FSTYPE --target "$DATA_MOUNT")
  options=$(findmnt -n -o OPTIONS --target "$DATA_MOUNT")
  [[ "$source_uuid" == "$expected_uuid" ]] || fail "/data source UUID mismatch: $source_uuid"
  [[ "$fstype" == "ext4" ]] || fail "/data fstype must be ext4; got $fstype"
  [[ ",$options," == *",nodev,"* ]] || fail "/data mount options missing nodev: $options"
  [[ ",$options," == *",nosuid,"* ]] || fail "/data mount options missing nosuid: $options"
}

verify_final_capacity() {
  CURRENT_PHASE="phase-7-final-verification"
  local root_size_bytes data_size_bytes vg_free_bytes
  root_size_bytes=$(lvs --noheadings --units b --nosuffix -o lv_size "$ROOT_LV" | lvm_bytes)
  data_size_bytes=$(lvs --noheadings --units b --nosuffix -o lv_size "$DATA_LV" | lvm_bytes)
  vg_free_bytes=$(vgs --noheadings --units b --nosuffix -o vg_free "$EXPECTED_VG" | lvm_bytes)
  [[ "$root_size_bytes" == "$ROOT_FINAL_BYTES" ]] || fail "root LV is not 150G in final verification; got ${root_size_bytes} bytes"
  [[ "$data_size_bytes" == "$DATA_SIZE_BYTES" ]] || fail "data LV is not 700G in final verification; got ${data_size_bytes} bytes"
  (( vg_free_bytes >= RESERVED_VG_FREE_AFTER_BYTES )) || fail "VG free after apply ${vg_free_bytes} bytes ($(format_gib "$vg_free_bytes")) is below required reserve ${RESERVED_VG_FREE_AFTER_BYTES} bytes ($(format_gib "$RESERVED_VG_FREE_AFTER_BYTES"))"
  info "Final VG free: ${vg_free_bytes} bytes ($(format_gib "$vg_free_bytes"))."
  info "Required final VG reserve: ${RESERVED_VG_FREE_AFTER_BYTES} bytes ($(format_gib "$RESERVED_VG_FREE_AFTER_BYTES"))."
}

apply_changes() {
  preflight_apply

  CURRENT_PHASE="phase-1-lvm-metadata-backup"
  log "Phase 1 -- LVM metadata backup"
  vgcfgbackup "$EXPECTED_VG"

  CURRENT_PHASE="phase-2-extend-root"
  log "Phase 2 -- Extend root LV to 150G"
  lvextend -L 150G "$ROOT_LV"
  if ! resize2fs "$ROOT_LV"; then
    fail "resize2fs failed after lvextend. Do not shrink the LV. Inspect ext4 state manually before continuing. Data LV was not created."
  fi
  verify_root_after_resize

  CURRENT_PHASE="phase-3-create-data-lv"
  log "Phase 3 -- Create and format data LV"
  lvcreate -L 700G -n "$DATA_LV_NAME" "$EXPECTED_VG"
  verify_new_data_lv_empty
  if ! mkfs.ext4 -L "$DATA_LABEL" -m 1 "$DATA_LV"; then
    fail "mkfs.ext4 failed. The data LV may exist and is not automatically removed. Inspect $DATA_LV manually."
  fi
  local data_uuid
  data_uuid=$(verify_data_filesystem)
  info "data_uuid=$data_uuid"

  CURRENT_PHASE="phase-4-prepare-mountpoint"
  log "Phase 4 -- Prepare mountpoint"
  install -d -o root -g root -m 755 "$DATA_MOUNT"
  [[ ! -L "$DATA_MOUNT" ]] || fail "$DATA_MOUNT became a symlink"
  if findmnt --mountpoint "$DATA_MOUNT" >/dev/null 2>&1; then
    fail "$DATA_MOUNT is already mounted before mount phase"
  fi

  log "Phase 5 -- Safely update /etc/fstab"
  update_fstab "$data_uuid"

  CURRENT_PHASE="phase-6-mount-data"
  log "Phase 6 -- Mount /data and create project data root"
  if ! mount "$DATA_MOUNT"; then
    fail "mount /data failed. LV/filesystem/fstab are preserved for manual inspection; no automatic LVM rollback was attempted."
  fi
  verify_data_mount "$data_uuid"
  install -d -o hui -g hui -m 750 "$PROJECT_DATA"

  CURRENT_PHASE="phase-7-final-verification"
  log "Phase 7 -- Final verification"
  pvs -o pv_name,vg_name,pv_fmt,pv_attr,pv_size,pv_free
  vgs -o vg_name,vg_attr,vg_size,vg_free,pv_count,lv_count,snap_count
  lvs -a -o lv_name,vg_name,lv_attr,lv_size,segtype,origin,pool_lv,data_percent,metadata_percent,devices
  lsblk -e7 -o NAME,KNAME,PATH,SIZE,TYPE,FSTYPE,FSVER,MOUNTPOINTS,UUID,MODEL
  findmnt "$DATA_MOUNT"
  df -hT / "$DATA_MOUNT"
  blkid "$DATA_LV"
  stat -c '%n|%F|%U|%G|%a|%s|%y' "$DATA_MOUNT" "$PROJECT_DATA"
  awk '$2 == "/data" {print}' /etc/fstab
  verify_final_capacity
  [[ -d "$PROJECT_REPO/.git" ]] || fail "project Git repository is missing or moved"

  log "Apply complete"
  info "A separate, controlled reboot persistence verification is still required."
}

print_dry_run() {
  CURRENT_PHASE="dry-run"
  log "Dry-run only -- no storage changes will be made"
  require_host
  info "Host check passed: $(hostname)"
  info "Current user: $(id -un)"
  info "Effective UID: ${EUID}"
  info "Project repo: $PROJECT_REPO"
  [[ -d "$PROJECT_REPO" ]] && info "Project repo exists" || info "Project repo missing"

  log "Non-mutating checks"
  findmnt --real
  df -hT / || true
  if [[ -e "$DATA_MOUNT" ]]; then
    info "$DATA_MOUNT exists; --apply preflight would stop unless this is expected and reviewed."
    ls -ld "$DATA_MOUNT" || true
  else
    info "$DATA_MOUNT does not exist."
  fi
  if awk '$2 == "/data" {found=1} END {exit found ? 0 : 1}' /etc/fstab; then
    info "/etc/fstab already has a /data mount target; --apply would stop."
  else
    info "/etc/fstab has no /data mount target."
  fi

  log "Root-only preflight"
  if [[ "${EUID}" -ne 0 ]]; then
    info "Not running as root. Full LVM preflight and apply require: sudo $0 --apply"
  else
    info "Running as root. Use --apply to execute; dry-run still makes no changes."
  fi

  log "Proposed plan"
  cat <<PLAN
1. Verify exact host, user/group, PV, VG, LV, filesystem, fstab, and capacity state.
2. Run: vgcfgbackup $EXPECTED_VG
3. Run: lvextend -L 150G $ROOT_LV
4. Run: resize2fs $ROOT_LV
5. Run: lvcreate -L 700G -n $DATA_LV_NAME $EXPECTED_VG
6. Run: mkfs.ext4 -L $DATA_LABEL -m 1 $DATA_LV
7. Create $DATA_MOUNT as root:root 755.
8. Add UUID-based /etc/fstab entry with defaults,nodev,nosuid.
9. Mount $DATA_MOUNT.
10. Create $PROJECT_DATA as hui:hui 750.
11. Verify root=150G, data=700G, /data mounted, and project repo remains in place.
PLAN
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
    print_dry_run
  fi
}

main "$@"

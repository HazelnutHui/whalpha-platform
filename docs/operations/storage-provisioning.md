# Workstation Storage Provisioning

Status: Approved, Not Yet Executed

This document describes the approved storage implementation for the workstation. It records the operator workflow and the safety boundaries for `scripts/admin/provision-workstation-storage.sh`.

Do not store or paste passwords in this repository, shell commands, files, environment variables, or chat. Run this procedure only directly on `dell5820`.

## Verified Pre-Change Storage Facts

Confirmed by final interactive sudo verification:

- PV: `/dev/nvme0n1p3`
- VG: `ubuntu-vg`
- VG size: less than 950.82G
- VG free: less than 850.82G
- Only LV: `ubuntu-lv`
- Root LV size: 100.00G
- Root LV type: linear
- Root filesystem: ext4
- Snapshot count: 0
- No thin pool, cache LV, or other LV
- `/data` does not exist
- `/etc/fstab` has no `/data` entry
- `findmnt` verification reported 0 parse errors and 0 errors
- Existing swap-file warning is known and not part of this change
- LVM metadata backup/archive exists

## Target Layout

- Root LV: extend to 150G
- Data LV: `trading-data`, 700G
- Data filesystem: ext4
- Filesystem label: `TIP_DATA`
- ext4 reserved blocks: 1%
- Mountpoint: `/data`
- Mount options: `defaults,nodev,nosuid`
- Project data root: `/data/trading-intelligence-platform`
- `/data` owner/mode: `root:root`, `755`
- Project data root owner/mode: `hui:hui`, `750`
- Expected retained VG free: approximately 100.82G

## Why Separate Code and Data

The source repository remains under `/home/hui/projects/trading-intelligence-platform`. Market data, derived datasets, cache-like artifacts, and future large local storage should live under `/data/trading-intelligence-platform`.

This keeps Git history, application code, and operational data separate. It also allows the data volume to grow independently from the root filesystem.

## Script Path

```bash
scripts/admin/provision-workstation-storage.sh
```

The script defaults to dry-run. It only modifies storage when `--apply` is explicitly provided.

## Dry-Run Command

```bash
sudo scripts/admin/provision-workstation-storage.sh
```

Dry-run prints the proposed plan and performs only non-mutating checks. It must not create LVM metadata backups, create `/data`, modify filesystems, or edit `/etc/fstab`.

## Apply Command

```bash
sudo scripts/admin/provision-workstation-storage.sh --apply
```

Apply mode must run as root. It performs strict preflight checks before any modification.

## Expected Final Layout

After successful apply:

- `/dev/ubuntu-vg/ubuntu-lv` is 150G and remains mounted at `/`
- `/dev/ubuntu-vg/trading-data` is 700G
- `/dev/ubuntu-vg/trading-data` has ext4 label `TIP_DATA`
- `/data` is mounted from the new data filesystem
- `/data/trading-intelligence-platform` exists and is owned by `hui:hui`
- The project Git repository remains at `/home/hui/projects/trading-intelligence-platform`

## Irreversible Boundaries

- Root LV expansion should be treated as irreversible for this project.
- The script must not attempt to shrink the root LV.
- The script must not delete a newly created data LV automatically.
- The script must not reformat an already formatted data LV.

## Partial-Failure Handling

- If `lvextend` succeeds but `resize2fs` fails, stop immediately. Do not shrink the LV. Inspect the filesystem manually before continuing.
- If `lvcreate` succeeds but `mkfs.ext4` fails, stop immediately. The data LV may exist and is not automatically removed.
- If `/etc/fstab` verification fails, the script restores the pre-change fstab backup and stops.
- If mounting `/data` fails, the LV, filesystem, and fstab state are preserved for manual inspection. No automatic LVM rollback is attempted.
- Re-running `--apply` after a partial implementation must stop during preflight rather than guessing how to continue.

## Post-Apply Verification

The script prints and verifies:

- `pvs`
- `vgs`
- `lvs`
- `lsblk`
- `findmnt /data`
- `df -hT / /data`
- `blkid` for the data LV
- `/data` owner/mode
- project data root owner/mode
- `/etc/fstab` new `/data` entry
- root LV is 150G
- data LV is 700G
- root mount remains normal
- `/data` mount is normal
- project Git repository was not moved

## Reboot Persistence Verification

The script does not reboot. After a successful apply, schedule a separate controlled reboot verification:

1. Confirm active SSH access before reboot.
2. Reboot only when no active work depends on the workstation.
3. After reboot, reconnect to `dell5820`.
4. Verify `/` and `/data` mounts with `findmnt --real` and `df -hT / /data`.
5. Verify the project repository and `/data/trading-intelligence-platform` both exist.

## Operational Boundaries

- Do not run this script on any host except `dell5820`.
- Do not modify `/etc/fstab` by hand unless recovering from a documented failure.
- Do not add extra data subdirectories until the application design requires them.
- Do not store secrets, credentials, API keys, or provider tokens under Git.

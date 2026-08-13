# Workstation Storage Provisioning

Status: Completed and Reboot-Verified

Execution date: 2026-08-13

This document records the completed workstation storage implementation and the safety boundaries for `scripts/admin/provision-workstation-storage.sh`.

The provisioning script is a one-time guarded procedure. Do not run `--apply` again on the completed host. The current-state preflight should intentionally reject reapplication because the root LV has already been expanded, the data LV exists, `/data` exists, and `/etc/fstab` contains the completed mount entry.

The script remains in the repository as an auditable operational record. Future storage changes require a new reviewed procedure, not modification or blind rerun of this completed operation.

Do not store or paste passwords in this repository, shell commands, files, environment variables, or chat. Run any storage procedure only directly on `dell5820`.

## Verified Pre-Change Storage Facts

Confirmed before the completed implementation:

- PV: `/dev/nvme0n1p3`
- VG: `ubuntu-vg`
- Only LV: `ubuntu-lv`
- Root LV size before change: 100.00G
- Root LV type: linear
- Root filesystem: ext4
- Snapshot count: 0
- No thin pool, cache LV, or other LV
- `/data` did not exist
- `/etc/fstab` had no `/data` entry
- `findmnt` verification reported 0 parse errors and 0 errors
- Existing swap-file warning was known and not part of this change
- LVM metadata backup/archive existed

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
- Preflight minimum VG free before changes: at least 850 GiB
- Required retained VG free after changes: at least 100 GiB

## Completed Result

- Preflight passed.
- LVM metadata backup completed.
- Root LV extended online from 100 GiB to 150 GiB.
- Root ext4 filesystem resized successfully.
- `trading-data` LV created at 700 GiB.
- ext4 filesystem created with label `TIP_DATA` and 1% reserved blocks.
- UUID-based `/etc/fstab` entry installed.
- Mount options include `nodev,nosuid`.
- `/data` mounted successfully.
- Project data root created at `/data/trading-intelligence-platform`.
- Final VG free is approximately 100.82 GiB.
- Controlled reboot verified persistent `/data` mount.
- No failed systemd units were present after reboot verification.

## Why Separate Code and Data

The source repository remains under `/home/hui/projects/trading-intelligence-platform`. Market data, derived datasets, cache-like artifacts, and future large local storage should live under `/data/trading-intelligence-platform`.

This keeps Git history, application code, and operational data separate. It also allows the data volume to grow independently from the root filesystem.

## Script Path

```bash
scripts/admin/provision-workstation-storage.sh
```

The script defaults to dry-run. It only modifies storage when `--apply` is explicitly provided. Invalid or extra arguments are rejected before apply preflight.

## Historical Execution Commands — Do Not Rerun on the Provisioned Host

These commands are retained only to document how the completed procedure was designed to run.

Dry-run command:

```bash
sudo scripts/admin/provision-workstation-storage.sh
```

Apply command:

```bash
sudo scripts/admin/provision-workstation-storage.sh --apply
```

Do not run the apply command again on `dell5820`. Reapplication should fail preflight on the completed host, and future storage changes must use a new reviewed procedure.

## Final Layout

After successful implementation:

- `/dev/ubuntu-vg/ubuntu-lv` is 150G and remains mounted at `/`
- `/dev/ubuntu-vg/trading-data` is 700G
- `/dev/ubuntu-vg/trading-data` has ext4 label `TIP_DATA`
- `/data` is mounted from the data filesystem
- `/data/trading-intelligence-platform` exists and is owned by `hui:hui`
- The project Git repository remains at `/home/hui/projects/trading-intelligence-platform`
- Approximately 100.82 GiB VG free remains available for future expansion

## Irreversible Boundaries

- Root LV expansion should be treated as irreversible for this project.
- The script must not attempt to shrink the root LV.
- The script must not delete a newly created data LV automatically.
- The script must not reformat an already formatted data LV.

## Partial-Failure Handling

- If `lvextend` succeeds but `resize2fs` fails, stop immediately. Do not shrink the LV. Inspect the filesystem manually before continuing.
- If `lvcreate` succeeds but `mkfs.ext4` fails, stop immediately. The data LV may exist and is not automatically removed.
- If `/etc/fstab` verification fails, the script restores the pre-change fstab backup with a same-directory temporary file and atomic rename, then stops.
- If mounting `/data` fails, the LV, filesystem, and fstab state are preserved for manual inspection. No automatic LVM rollback is attempted.
- Re-running `--apply` after a partial implementation must stop during preflight rather than guessing how to continue.

## Post-Apply Verification Record

The completed procedure verified:

- LVM and filesystem layout
- `/data` mount state
- root LV size
- data LV size
- retained VG free
- `/data` owner/mode
- project data root owner/mode
- `/etc/fstab` mount entry presence
- project Git repository location

## Reboot Persistence Verification

A separate controlled reboot verification was completed on 2026-08-13:

1. SSH access remained healthy.
2. `/data` mounted automatically after reboot.
3. The project repository remained under `/home/hui/projects/trading-intelligence-platform`.
4. `/data/trading-intelligence-platform` remained available.
5. No failed systemd units were present after reboot.

## Operational Boundaries

- Do not run this script on any host except `dell5820`.
- Do not rerun `--apply` on the completed host.
- Do not modify `/etc/fstab` by hand unless recovering from a documented failure.
- Do not add extra data subdirectories until the application design requires them.
- Do not store secrets, credentials, API keys, or provider tokens under Git.

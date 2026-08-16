# Infrastructure

This document records non-sensitive infrastructure facts. Do not add literal server IPs, OCIDs, key paths, credentials, fingerprints, filesystem UUIDs, or authorized key contents.

## Workstation

Confirmed:

- SSH alias: `dell5820`
- hostname: `dell5820`
- Ubuntu Server 24.04.4 LTS
- Dell Precision 5820
- Intel Xeon W-2145
- 8 physical cores / 16 threads
- approximately 62 GiB RAM
- approximately 1 TB NVMe
- LVM volume group: `ubuntu-vg`
- root LV: `ubuntu-lv`, 150 GiB, ext4, mounted at `/`
- data LV: `trading-data`, 700 GiB, ext4, mounted at `/data`
- data filesystem label: `TIP_DATA`
- persistent `/data` mount configured by UUID
- `/data` mount options include `nodev,nosuid`
- approximately 100.82 GiB VG free retained
- `/home/hui/projects` is the code parent directory
- project data root: `/data/trading-intelligence-platform`
- project data root owner/mode: `hui:hui`, `750`
- reboot persistence verified on 2026-08-13
- systemd failed units after verification: 0
- Docker was not installed at last verification
- Python 3.12.3 and Git 2.43.0 were available
- Node.js 24 LTS and npm are available for frontend development

## OCI

The following is the last known state recorded by Git history and deployment documentation, not a current live-health assertion. The most recent recorded deployment is private Dashboard disclosure release `2026-08-14T020535Z-ebb16015b7da`, built from commit `ebb16015b7da259e68033ca442544def5a300d63`. It uses `/` as the branded session-login entry, `/login/` as a compatibility redirect, and a shared server-side session boundary for `/dashboard/` and `/private-data/`. OCI was not accessed during the 2026-08-16 documentation reconciliation, so current services, checksums, listeners, TLS, and routes were not re-verified. Do not record literal public IP addresses, SSH key material, password hashes, or credential contents here.

Last recorded infrastructure facts:

- SSH alias: `whalpha-oci`
- instance name: HUI
- hostname: `hui`
- Ubuntu 22.04.5 LTS
- VM.Standard.E2.1.Micro
- 2 vCPU
- approximately 1 GiB RAM
- approximately 45G root disk
- no swap
- Nginx and Certbot were retained
- HTTPS and the public/private route boundary passed the recorded deployment checks
- a localhost-only session Auth Service, Nginx `auth_request`, and versioned static releases were deployed and verified at the recorded time
- no production FastAPI market-data service was deployed to OCI

Before relying on any current OCI claim, perform a separately authorized read-only operational verification. Historical preflight statements describing `/srv/whalpha` as absent or `/` as a static placeholder were superseded by the recorded private Dashboard deployments.

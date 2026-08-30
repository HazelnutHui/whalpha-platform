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

Live-verified through the `whalpha-oci` SSH alias on 2026-08-30 without reading
credentials. The active Dashboard release is
`2026-08-28T141747Z-83f9b629279c`; `/` is the data-free branded credential/guest
Session entry, and `/dashboard/` and `/private-data/` share the server-side
Session boundary.

Confirmed infrastructure facts:

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
- Nginx and the Session Auth Service are active and enabled
- the Auth Service listens only on `127.0.0.1:8010`
- loopback HTTPS checks passed the unauthenticated route boundary, and a
  temporary guest Session read the same Dashboard and Snapshot before logout
- the active release passed exact remote preflight and postflight; the complete
  remote retained-release inventory must be reread before any cleanup
- no release staging/partial residue exists
- no production FastAPI market-data service was deployed to OCI

Do not record literal public IP addresses, SSH key material, password hashes, or
credential contents here. Password-based browser behavior remains a manual
user check.

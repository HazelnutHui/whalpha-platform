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

The private static Dashboard release `2026-08-13T120220Z-987b5289a783` is deployed under the reviewed `/srv/whalpha` release layout. Public `/` remains the WH Alpha placeholder; private `/dashboard/` and `/private-data/` require Basic Auth. Do not record literal public IP addresses, SSH key material, password hashes, or credential contents here.

Confirmed:

- SSH alias: `whalpha-oci`
- instance name: HUI
- hostname: `hui`
- Ubuntu 22.04.5 LTS
- VM.Standard.E2.1.Micro
- 2 vCPU
- approximately 1 GiB RAM
- approximately 45G root disk
- no swap
- Nginx and Certbot retained
- whalpha.com and www.whalpha.com have working HTTPS
- current page is a static placeholder
- read-only preflight on 2026-08-15 confirmed Nginx active/enabled, public HTTP 301, public HTTPS 200, no failed units, `/srv/whalpha` absent, and auth directory absent

- no application backend is running
- 8000 and 8001 have no listeners

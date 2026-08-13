# Infrastructure

This document records non-sensitive infrastructure facts. Do not add literal server IPs, OCIDs, key paths, credentials, fingerprints, or authorized key contents.

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
- LVM
- current root LV: 100G
- approximately 850G VG free as last verified
- `/home/hui/projects` is currently the code parent directory
- Docker and Node were not installed at last verification
- Python 3.12.3 and Git 2.43.0 were available

## OCI

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
- no application backend is running
- 8000 and 8001 have no listeners

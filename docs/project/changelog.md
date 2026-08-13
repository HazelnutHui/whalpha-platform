# Changelog

## 2026-08-13

- Expanded workstation root LV from 100 GiB to 150 GiB.
- Created 700 GiB ext4 data LV mounted at `/data`.
- Created `/data/trading-intelligence-platform`.
- Retained approximately 100.82 GiB VG free.
- Verified `/data` persisted across a controlled reboot.
- Confirmed zero failed systemd units after reboot.
- Documented the accepted application technology stack.
- Documented the target application architecture.
- Added the documentation checkpoint policy for future material changes.
- Created the minimal FastAPI backend scaffold.
- Created the minimal React/Vite frontend scaffold.
- Introduced the versioned Health API contract.
- Added local development scripts and documentation.
- Installed backend dependencies in the project virtualenv and verified backend tests.
- Verified the Health API locally on `127.0.0.1:8000`.
- Frontend dependency installation and build were not verified because Node.js and npm were unavailable.
- Prepared guarded Node.js 24 LTS provisioning script and operations document.
- Node.js provisioning was not applied because passwordless sudo is unavailable.
- No market data provider, database, production deployment, or Dashboard V1 implementation was introduced.

## 2026-08-12

- Completed workstation and OCI infrastructure audits.
- Removed obsolete projects and services.
- Replaced old public trading console with static placeholder.
- Separated workstation and OCI SSH identities.
- Established initial product, architecture, and Dashboard V1 decisions.
- Created project documentation foundation.

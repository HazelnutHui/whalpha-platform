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
- Completed Node.js 24 LTS provisioning and verified npm.
- Corrected provisioning script GPG behavior to avoid interactive overwrite prompts.
- Locked frontend dependencies with npm-generated `package-lock.json`.
- Verified frontend production build.
- Verified local Vite server and Vite-to-FastAPI proxy.
- Revalidated backend tests and the direct Health API endpoint.
- No market data provider, database, production deployment, or Dashboard V1 implementation was introduced.
- Accepted the Initial EOD Universe boundary.
- Accepted the three-layer classification model for Sector/Industry, Theme, and Analytical Groups.
- Accepted five normalized EOD logical contracts.
- Documented point-in-time membership and revision principles.
- No provider, data ingestion, physical schema, database, or Dashboard implementation was introduced.
- Implemented the Instrument Master V1 Pydantic contract.
- Implemented the EOD Price Bar V1 Pydantic contract.
- Added validation and serialization tests for the two implemented contracts.
- No provider adapter, persistence, real market data, database, or Dashboard implementation was introduced.

## 2026-08-12

- Completed workstation and OCI infrastructure audits.
- Removed obsolete projects and services.
- Replaced old public trading console with static placeholder.
- Separated workstation and OCI SSH identities.
- Established initial product, architecture, and Dashboard V1 decisions.
- Created project documentation foundation.

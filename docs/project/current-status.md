# Current Status

Status date: 2026-08-12

## Completed

- Workstation infrastructure audited.
- Old workstation application, service, cron, and port-8088 process removed.
- Old workstation project directory removed.
- Workstation `authorized_keys` reduced to its dedicated WSL ED25519 key.
- OCI infrastructure audited.
- Old V3 Trading Console removed without backup by explicit user decision.
- Old OCI FastAPI/Uvicorn service removed.
- Old OCI project and data directories removed.
- Nginx, Certbot, TLS, and SSH retained.
- whalpha.com now serves a static placeholder.
- Dedicated SSH identities and aliases created for both servers.
- Obsolete shared RSA access removed and local old RSA files deleted.
- Product direction and Dashboard V1 scope confirmed.

## Current

- Project documentation bootstrap.
- No application code.
- No production data ingestion.
- No database.
- No selected Web framework.
- No selected deployment workflow.
- No API credentials configured.
- No data LV created yet.

## Next Proposed Step

Validate and implement workstation storage layout:

- root LV proposed to expand from 100G to 150G
- proposed `/data` LV of 700G
- retain approximately 100G VG free

Then create the minimal application scaffold.

This storage work is proposed and has not yet been executed.

# Current Status

Status date: 2026-08-14

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
- Workstation storage layout implemented and reboot-verified.
- Root LV expanded to 150 GiB.
- Independent 700 GiB `/data` LV created.
- Project data root created at `/data/trading-intelligence-platform`.
- Approximately 100.82 GiB VG free retained.
- Application technology stack decision accepted.
- Target application architecture documented.
- Minimal backend scaffold created.
- Minimal frontend scaffold created.
- Versioned Health API contract introduced.
- Local development scripts added.
- Scaffold development documentation added.
- Node.js 24 LTS and npm toolchain installed and verified.
- Frontend dependencies installed and locked with `package-lock.json`.
- Frontend production build verified.
- Local Vite development server verified.
- Local Vite-to-FastAPI proxy verified.
- Node provisioning script GPG non-interactive behavior corrected.
- Initial EOD Universe boundary accepted.
- Three-layer classification boundary accepted.
- Five normalized EOD logical contracts accepted.
- Point-in-time universe membership semantics accepted.
- Provider-neutral boundary clarified for EOD contracts.
- Instrument Master V1 Python contract implemented.
- EOD Price Bar V1 Python contract implemented.
- Contract validation test suite added for Instrument Master V1 and EOD Price Bar V1.
- Minimal synchronous MarketDataProvider Protocol implemented.
- ProviderCapability declarations implemented for Instrument Master and EOD Price Bars.
- InstrumentQuery and EodBarQuery implemented.
- Revision-selection semantics implemented for EOD bars.
- Provider exception taxonomy implemented.
- Deterministic in-memory provider boundary tests added.
- First real EOD provider evaluation completed.
- Massive Stocks Basic selected for private EOD development.
- Licensing and access boundary documented for provider-backed data and derived works.
- Public placeholder, public data-free demo, and private real-data dashboard separation documented.
- Massive configuration and credential boundary implemented.
- Massive mocked HTTP transport boundary implemented.
- Massive mocked adapter skeleton implemented for Instrument Master and EOD Price Bars.
- Massive adapter tests added with deterministic mocked responses and no network access.
- Massive credential file manually provisioned outside Git with protected owner and mode.
- Massive credential loader implemented with strict file and parser validation.
- Massive standard-library HTTPS transport implemented.
- One read-only Massive Stocks reference smoke test verified authentication and reference entitlement.
- One-session provider-neutral EOD ingestion service implemented for mocked fixtures.
- EOD Price Bar V1 Parquet repository implemented with explicit PyArrow schema.
- Deterministic content fingerprint and manifest metadata implemented.
- Atomic partition publishing, idempotent rerun detection, conflict rejection, and corruption checks implemented.
- Mocked-fixture ingestion and Parquet persistence tests added.
- One read-only Massive Grouped Daily inspection completed for 2026-08-13.
- Grouped Daily access and payload structure verified.
- Production publication blocked pending Instrument Master identity coverage.
- Provider Instrument Identity V1 Python contract implemented.
- Stable provider-identifier UUIDv5 identity resolution implemented.
- Massive All Tickers point-in-time snapshot ingestion path implemented with bounded pagination and rate-aware requests.
- Corrected Massive All Tickers snapshot completed and published for 2026-08-13 after refining expected exclusions, eligible coverage, and ticker ambiguity gates.
- Grouped Daily parser, identity-ordering, and duplicate-isolation fixes implemented and tested.
- The latest authorized 2026-08-13 Grouped Daily request passed identity coverage but failed numeric conversion and canonical bar count gates without publishing EOD bars.

## Current

- Documentation and infrastructure foundation complete.
- Application stack and target architecture documented.
- Backend scaffold exists under `apps/api`.
- Frontend scaffold exists under `apps/web`.
- Python virtualenv created at the project root and ignored by Git.
- Backend dependencies installed in the project virtualenv.
- Backend tests verified: `300 passed`.
- Health endpoint verified locally on `127.0.0.1:8000`.
- Node.js 24 LTS and npm are installed and verified.
- Frontend dependencies are installed and locked by npm.
- Frontend production build is verified.
- Local Vite development server and Vite-to-FastAPI proxy are verified.
- Initial EOD Universe, classification boundary, and normalized EOD logical contracts are documented.
- Instrument Master V1 and EOD Price Bar V1 Python/Pydantic contracts are implemented and tested.
- No physical schemas.
- Corporate Action V1, Classification V1, and Universe Membership V1 Python models are not implemented.
- No Parquet writers beyond the mocked-fixture EOD Price Bar V1 repository.
- Minimal provider boundary Protocol is implemented.
- Massive Stocks Basic is selected for private EOD development only.
- Massive mocked adapter skeleton exists with injected fake transport tests.
- Massive credential exists outside Git in the protected workstation credential file.
- Massive Stocks reference authentication and entitlement have been smoke-test verified once.
- No ingestion API calls beyond the one reference smoke test.
- No Grouped Daily production download beyond the one in-memory inspection request.
- No production `/data` writes for EOD bars; the latest 2026-08-13 Grouped Daily publication attempt was blocked by required numeric-field semantics.
- Completed Instrument Master, provider identity, and provider ticker resolver snapshots exist for 2026-08-13 under `/data/trading-intelligence-platform`.
- No historical backfill.
- Production Instrument Master, provider identity, and provider ticker resolver snapshots exist for 2026-08-13; no production EOD Price Bar dataset exists.
- Mocked-fixture tests write temporary Parquet partitions only under pytest `tmp_path`.
- No private access-control mechanism selected.
- No private access-control implementation.
- No market data ingestion.
- No actual Universe evaluation.
- No actual taxonomy dataset.
- No analytics pipeline.
- No Dashboard V1 implementation.
- No database.
- No deployment pipeline.
- No production application.
- No API credentials stored in Git, documentation, frontend code, logs, or command arguments.
- Project data root exists but contains no project datasets yet.

## Next Proposed Step

Resolve the Massive Grouped Daily required numeric-field semantics with field-level diagnostics and an explicit contract decision before any further live Grouped Daily request or EOD bar publication attempt.

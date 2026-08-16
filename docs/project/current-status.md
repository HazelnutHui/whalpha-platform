# Current Status

Status date: 2026-08-16

## Completed

- Implemented Phase B2B bounded SEC transport, atomic source-cache safeguards, safe ZIP selection, normalized observation persistence, canonical evidence persistence, and logical completion contracts with deterministic offline tests.
- The first authorized B2B run made three requests and zero retries, then failed closed because the first SEC landing page did not yield exactly one official CSV candidate. No source cache or evidence dataset was published; production Universe, Dashboard, and OCI remain unchanged.
- Replaced the invalid single-link assumption with an offline-tested dated-table selector that ignores XML, filters future releases, rejects ambiguous or unsafe candidates, and records deterministic selection statistics. A new live run still requires explicit one-run authorization.
- The second authorized run used the dated selector but again stopped after request 3 at the first landing-page discovery gate (`sec_csv_discovery_cardinality_failure`), with zero retries. No completed cache/evidence, shadow audit, snapshot, Universe change, or OCI deployment resulted.
- Completed a second, network-free parser remediation after confirming the official pages use multiple tables with a `File / Format / Size` download table, anchor-label years, and anchor-tail `Updated` dates. The parser now has dataset-specific exact URL rules, historical-undated handling, bounded content-safe diagnostics, and selected-CSV content-type/schema checks. No SEC/Massive request, credential access, `/data` access, snapshot, deployment, or OCI access occurred.
- Set the bounded SEC live entrypoint to zero retries in commit `780425397c2bb3de3c389c195909790e94c039ad`; the generic transport and other providers retain their existing policies.
- The next single authorized SEC run made three requests and zero retries, then failed closed on `href_rejected` while parsing the Investment Company Series/Class landing page. No CSV or later source was requested, no completed cache/evidence was published, staging was clean, and the 34-file protected-data inventory remained identical.
- Completed a network-free diagnostic-contract remediation: landing discovery schema `2.0` now records bounded candidate/table/row context, parsed year/date, safe Size, public path structure, and finite URL failure codes beneath the compatible top-level `href_rejected` reason. The exact dataset allowlists and selection behavior are unchanged; the third live candidate remains unknown until separately observed. No credential or `/data` access, snapshot, bundle, OCI access, or deployment occurred.
- Executed the one separately authorized post-schema run once. It made three SEC requests and zero retries, then failed closed at Series/Class discovery with `href_rejected` / `path_template_mismatch`. Candidate 3 was the 2024 CSV in the public `/files/investment/data/other/investment-company-series-and-class-information/` directory variant; query, fragment, and userinfo were absent. No CSV or later source was requested, all four completed SEC targets remained absent, staging was zero, and the 34-file protected inventory was unchanged. The allowlist was not changed and no second run occurred.
- Added offline support for exactly that observed 2024 Series/Class legacy path and basename, without extending the rule to 2023 or earlier, 2025, 2026, future years, CEF, or BDC. Candidate diagnostics are now the single source for aggregate discovery counts; the fourth-run failure shape reports two eligible candidates rather than zero, and the accepted three-candidate fixture selects 2026 with eligible count three. No new live run, credential access, `/data` access, or deployment operation occurred.

- Completed Security Evidence Phase B2A offline: SEC issuer-evidence observation/canonical contracts, point-in-time filing interpretation, stable-identity reconciliation, deterministic Core/Broad rules, secure private User-Agent configuration tooling, transport policy, and tmp-only Parquet persistence tests.
- Phase B2A made zero SEC/Massive requests, configured no real User-Agent, wrote no production `/data`, changed no Dashboard calculations, generated no snapshot, and performed no OCI deployment. Core/Broad production activation remains deferred.

- Product policy selected: Core U.S. Domestic Operating Equities future default; Broad U.S.-Listed Operating Equities future secondary; production activation deferred.
- Published the completed 2026-08-14 provider security evidence snapshot: 25 catalog types, 13,110 observations, 9,939 canonical evidence records, and a verified logical completion marker. The corrected run used 15 requests and zero retries.
- Implemented Provider Security Type Catalog V1, Provider Security Observation V1, Canonical Provider Instrument Security Evidence V1, bounded Massive ingestion, logical completion, and atomic Parquet persistence with no canonical dataset mutation.
- Deployed the provisional Dashboard disclosure and governance metadata without changing the 1,864-member calculations.
- The first Phase B1 live attempt used 15 requests and zero retries, reconciled 13,110 raw records, but failed ambiguous and mapped-business-key gates. No evidence partition, snapshot, or OCI release was published.
- Phase B1A read-only reconciliation confirmed two duplicate-ticker groups, `BCPC` and `TPC`. Each combines one stable-ID resolved observation with one identifier-free excluded observation; old ticker fallback caused the four false ambiguous observations.
- Provider observations are now separate from canonical evidence. The corrected offline identity result is 9,939 canonical-mapped, 3,171 expected-unjoined, zero stable collision/ticker ambiguity, and linkage 9,939/9,939.
- Sanitized failed-run diagnostics are implemented outside completed evidence datasets, including pre-reconciliation transport failures with unknown statistics represented as null.
- The provider-evidence audit leaves Core at 0 and Broad at 1. Of the legacy 1,864, 1,862 remain quarantine, VCX is an authoritative exclusion, and AKAN is the one authoritative Broad candidate; issuer-structure coverage remains insufficient for activation.

- Accepted ADR 0015 for effective-dated Security Classification V1 and quarantine-first evidence governance.
- Completed the read-only 2026-08-14 security-type audit: Instrument Master 9,939; raw comparable 9,889; legacy default 1,864.
- Confirmed VCX as excluded closed-end-fund pollution, separated AKAN as a U.S.-listed foreign operating ordinary share, and quarantined 4,527 records lacking sufficient classification evidence.
- Computed non-production Phase A candidates: Core 0 and Broad 1. Product policy is selected, but production integration remains blocked by evidence coverage; current Dashboard membership is unchanged.
- Phase A made no Massive request, credential access, canonical `/data` write, production snapshot, frontend behavior change, or OCI deployment.

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
- The initial Grouped Daily inspection identity blocker was resolved by the completed 2026-08-13 Instrument Master and ticker resolver snapshots.
- Provider Instrument Identity V1 Python contract implemented.
- Stable provider-identifier UUIDv5 identity resolution implemented.
- Massive All Tickers point-in-time snapshot ingestion path implemented with bounded pagination and rate-aware requests.
- Corrected Massive All Tickers snapshot completed and published for 2026-08-13 after refining expected exclusions, eligible coverage, and ticker ambiguity gates.
- Grouped Daily parser, identity-ordering, duplicate-isolation, and Decimal aggregate-volume fixes implemented and tested.
- First canonical EOD Price Bar session published for 2026-08-13 with 9,901 records after all V1 quality gates passed.
- Canonical EOD read repository implemented with completed-session manifest, schema, fingerprint, and identity snapshot validation.
- Private EOD query service and FastAPI response contracts implemented.
- Private EOD routes are default-disabled and absent from default OpenAPI unless explicitly enabled.
- Local production read verification completed for the 2026-08-13 session without modifying `/data`.
- The 2026-08-12 Instrument Master, provider identity, provider ticker resolver, and canonical EOD Price Bar datasets are published under `/data/trading-intelligence-platform`.
- Close-to-close EOD return analytics implemented across the completed 2026-08-12 and 2026-08-13 sessions.
- Market Summary V1, liquidity-screened movers, paginated returns, and Liquidity Map V1 private API responses implemented.
- Local React Market Dashboard V1 implemented with API/demo modes, Market Pulse, breadth, up/down volume, liquidity-screened movers, Liquidity Map V1, and data-quality/session metadata.
- Frontend unit/component tests and production build verified for Dashboard V1.
- Private static dashboard snapshot exporter implemented.
- Frontend snapshot mode implemented for `/dashboard/` static deployment.
- Versioned OCI dashboard bundle builder implemented.
- Nginx private dashboard template and deployment script implemented.
- Dedicated `dell5820` to OCI deployment SSH key provisioned; the WSL OCI key was retained.
- Private Dashboard session-login release `2026-08-15T133119Z-137f244e8508` deployed to OCI from source commit `137f244e850890dba29ee55f3a16c92923416497`.
- Private Dashboard root-login release `2026-08-13T135949Z-92819ed17316` is deployed to OCI from source commit `92819ed17316c567c40b440f5c2e8487f9db4b53`.
- Public `/` is now the unauthenticated WH Alpha branded session-login entry.
- `/login/` redirects to `/` for compatibility.
- `/dashboard/` redirects unauthenticated users to `/?next=/dashboard/`; `/private-data/v1/manifest.json` returns unauthenticated 401 JSON.
- Password rotation helper is deployed at `/srv/whalpha/admin/rotate-whalpha-dashboard-password.sh` for user-run interactive rotation.
- Deployment status is `authenticated_private_dashboard_verified_by_user`.
- Branded `/login/` page and localhost-only server-side session Auth Service implemented.
- Browser-native Basic Auth replaced for Dashboard access.
- Dashboard Logout implemented for snapshot mode.
- Dashboard numeric presentation rules and card overflow handling fixed for percent, ratio, count, volume, and currency values.
- The `/login/` route now serves the branded login page with content-aware deployment verification; public `/` remains the data-free placeholder.
- The login form submission defect that navigated to `/auth/login` with `invalid_request` is fixed; the page now uses the JSON session-login client contract.

- Dashboard V1.1 professional overview cleanup implemented: default `Tradable U.S. Equities` universe, auxiliary universes, Sector Benchmark ETFs, Trading Activity Map naming, mover outlier isolation, and categorized Data Details.
- Dashboard V1.1 Market Overview trust/usability upgrade implemented: SPY/QQQ/IWM/DIA benchmark strip, Sector ETF relative-to-SPY performance, conservative freshness status, top-50 Trading Activity Map default, cleaner labels/search/detail panel behavior, and SNDK data-review documentation.
- Private Dashboard Market Overview release `2026-08-13T214820Z-32fed3a8b17b` is deployed to OCI from source commit `32fed3a8b17b020e00c33f839d2a12e9de50d855`.

## Current

- The workstation is the source of truth for code, processing, canonical Parquet, private analytics, and deployment artifacts.
- FastAPI health and default-disabled private EOD/market routes are implemented; no production FastAPI service is deployed.
- React Dashboard V1.1 supports API, demo, and private snapshot modes with Market Pulse, breadth, up/down volume, movers, benchmark context, Sector ETF relative performance, Trading Activity Map, freshness, and governance disclosure.
- Massive secure credential/transport, bounded All Tickers ingestion, Grouped Daily ingestion, provider security evidence, and fixture/fake-transport tests are implemented.
- Completed Instrument Master, provider identity, and ticker resolver logical snapshots exist for 2026-08-12, 2026-08-13, and 2026-08-14. Counts are 9,932/13,106/9,932 for the first two dates and 9,939/13,110/9,939 for 2026-08-14.
- Completed canonical EOD Price Bar partitions exist for 2026-08-12, 2026-08-13, and 2026-08-14 with 9,900, 9,901, and 9,912 records respectively.
- Completed 2026-08-14 provider security evidence contains 25 catalog records, 13,110 observations, 9,939 canonical evidence records, and a logical completion marker.
- SEC bounded transport, source-cache safety, parsers, evidence contracts/repositories, live CLI, retries=0 entrypoint, exact observed 2024 Series/Class legacy-path support, and candidate diagnostic schema `2.0` are implemented. Four authorized discovery runs failed closed; no later live run has exercised the offline path correction, and no completed SEC source cache, observation, canonical evidence, or logical snapshot exists.
- Core is the accepted future default and Broad the future secondary view, but production remains on the disclosed provisional legacy 1,864-member rule pending authoritative issuer-structure and domicile coverage.
- The 2026-08-14 identity snapshot is `accepted_with_provenance_exception`; its original request/pagination provenance is unknown and it must not be requested again or overwritten.
- Private JSON snapshot export, frontend snapshot build, versioned bundle creation, session-login configuration, and deployment tooling are implemented. Git records release `2026-08-14T020535Z-ebb16015b7da` as the last known OCI deployment; OCI was not accessed during the 2026-08-16 documentation reconciliation, so current live health is unverified.
- No historical backfill, automated daily ingestion, database/catalog service, corporate-action reconciliation, point-in-time sector taxonomy, market-cap dataset, Theme/relationship analytics, Options ingestion, or complete Event Engine exists.
- Ignored `build/`, `apps/web/dist`, historical snapshots, and historical bundles exist locally. They were not generated or removed by the documentation reconciliation; retention policy remains open.
- `/data` project subdirectories are group-writable in the observed metadata while the project root is mode `750`; the intended group-write policy is not yet documented and was not changed.
- Provider credentials remain outside Git. Ordinary tests use fixtures, injected fakes, and explicit socket-prohibition regressions.

## Offline Verification Baseline

Verified on 2026-08-16 for the docs-only status reconciliation:

- backend full: `619 passed`, `2 warnings`, `0 skipped`, `0 xfailed`
- SEC provider suite: `96 passed`; bulk discovery: `53 passed`; extended SEC contracts/persistence/operation set: `113 passed`
- explicit network/socket prohibition selection: `8 passed`, `611 deselected`
- frontend regression: `40 passed` across 5 files
- frontend production build: success, 589 modules transformed; output was directed to a temporary `/tmp` directory rather than a production snapshot/bundle
- Python compileall, required imports, Health contract, and `bash -n` for 15 shell scripts: passed
- Markdown local links: 82 files, 202 links checked, 0 failures
- sensitive-information scan: 264 tracked UTF-8 files, 0 high-confidence findings; synthetic credentialed-URL rejection fixtures were excluded only from that URL rule
- `git diff --check`: passed

Backend warnings are the existing Python `crypt` deprecation and Starlette TestClient/httpx migration warning. Frontend warnings are the existing Vite React-plugin configuration deprecations and one 639.01 kB minified chunk warning. No provider network request, credential read, `/data` write, OCI access, production snapshot/bundle generation, deployment, or artifact deletion occurred.

## SEC Schema 2.0 Run Postflight

Verified after the fourth authorized SEC run on 2026-08-16:

- focused SEC provider, issuer-evidence contract/persistence, and credential-script tests: `113 passed`, `0 warnings`, `0 skipped`, `0 xfailed`
- the temporary offline test guard recorded `0` external-network attempts
- Markdown local links: 82 files, 202 links checked, 0 failures
- sensitive-information scan: 264 tracked UTF-8 files, 0 high-confidence findings
- SEC live entrypoint `bash -n`, docs-only diff boundary, and `git diff --check`: passed

The live operation itself made only its three authorized SEC requests and zero retries. No Massive or OCI request, production snapshot/bundle generation, deployment, artifact deletion, code change, or test-semantics change occurred.

## Exact 2024 Series Path Offline Verification

Verified on 2026-08-16 after the exact-path and candidate-aggregate correction:

- bulk discovery: `72 passed`; all SEC provider tests: `115 passed`; extended SEC contracts/persistence/operation set: `132 passed`
- backend full: `638 passed`, `2 warnings`, `0 skipped`, `0 xfailed`
- explicit network/socket prohibition selection: `8 passed`, `630 deselected`, `2 warnings`; the external-network guard recorded 0 attempts throughout offline pytest runs
- frontend regression: `40 passed` across 5 files
- frontend production-mode build verification: success, 589 modules transformed, with output directed only to `/tmp`
- Python compileall, required imports, Health contract, and `bash -n` for 15 shell scripts: passed
- Markdown local links: 82 files, 202 links checked, 0 failures
- sensitive-information scan: 265 tracked-or-pending UTF-8 files, 0 high-confidence findings; synthetic credentialed-URL rejection fixtures were excluded only from that URL rule
- `git diff --check`: passed

Backend warnings remain the existing Python `crypt` deprecation and Starlette TestClient/httpx migration warning. Frontend warnings remain the existing Vite React-plugin configuration deprecations, external temporary `outDir` notice, and one 639.01 kB minified chunk warning. No SEC/Massive or other provider request, credential metadata/content access, `/data` access, OCI access, production snapshot/bundle generation, deployment, EOD/backfill/scheduler work, or live run occurred.

## Next Proposed Step

Review the completed exact-2024 offline contract and verification evidence before deciding whether to authorize at most one new bounded SEC run. This status is not live-run authorization; Core/Broad production activation remains deferred.

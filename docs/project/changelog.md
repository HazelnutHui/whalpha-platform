# Changelog

## 2026-08-16

- Added one exact offline Series/Class filename contract based only on the fifth run's schema `2.0` evidence: the modern directory plus `investment_company_series_class_2023.csv` is accepted only for parsed file year 2023. No rule is inferred for 2022 or earlier, and underscore basenames for 2024 and later remain rejected.
- Added a four-candidate official-shape fixture and regressions proving four allowlisted/cutoff-eligible candidates, zero rejected, exactly one deterministic 2026 selection, row-order independence, exact relative/absolute acceptance, URL-security rejection coverage, CEF/BDC isolation, duplicate stability, aggregate consistency, sentinel redaction, and zero external socket attempts.
- Preserved the modern Series/Class template, exact 2024 legacy-directory rule, CEF/BDC paths, cutoff, live retry setting, generic SEC transport, diagnostic schema `2.0`, and candidate-derived aggregates. No live run, credential metadata/content access, `/data` or OCI access, snapshot/bundle, deployment, EOD, backfill, scheduler, Dashboard, or Universe work occurred.

- Executed the separately authorized post-remediation SEC entrypoint exactly once. The run used cutoff 2026-08-14, made three SEC requests and zero retries, accepted the 2026 and 2025 modern Series/Class candidates plus the exact 2024 legacy candidate, then failed closed on a fourth 2023 underscore-style basename with `path_template_mismatch`.
- Real schema `2.0` aggregates remained consistent with candidate states: four CSV candidates, three allowlisted/cutoff-eligible, one rejected, and zero selected. No CSV, CEF, BDC, or submissions request followed; no rule was changed and no second run occurred.
- Published no SEC source cache, observation, canonical evidence, or logical manifest. Staging residue was zero, the 34-file protected inventory remained unchanged, and only the 4,798-byte sanitized diagnostic was retained. No Massive/OCI access, snapshot, bundle, deployment, EOD, backfill, scheduler, or Universe activation occurred.

- Added one exact offline Series/Class legacy-path rule based only on the fourth run's schema `2.0` evidence: the observed 2024 directory and 2024 basename are accepted only for file year 2024. The modern template remains valid; 2023-or-earlier, 2025, 2026, future legacy paths, neighboring spellings, CEF, and BDC remain rejected or unchanged.
- Made candidate diagnostics the single source for CSV candidate, allowlisted, parsed-date, future, historical-undated, rejected, cutoff-eligible, and selected aggregates. Added `selected_count` within compatible schema `2.0` and explicit duplicate exclusion so normal and mid-stream fail-closed diagnostics cannot drift from candidate states.
- Added an official-shape three-candidate fixture and regression coverage for deterministic 2026 selection, row reversal, relative/absolute exact-legacy acceptance, year/basename/directory and all URL safety rejections, aggregate consistency, other-dataset isolation, sentinel redaction, and socket prohibition. No live run, credential or `/data` access, provider request, OCI access, snapshot, bundle, deployment, EOD, backfill, or scheduler work occurred.

- Executed the separately authorized post-schema SEC evidence entrypoint exactly once with cutoff 2026-08-14. It ran from `2026-08-16T07:46:45Z` to `2026-08-16T07:46:51Z`, returned exit code 1, made three SEC requests and zero retries, and stopped at Investment Company Series/Class landing discovery; CEF, BDC, submissions, Massive, OCI, and all other endpoints were not reached.
- Captured sanitized schema `2.0` evidence for three Series/Class CSV candidates. The 2026 and 2025 candidates matched the current path template; the 2024 candidate used the public `investment-company-series-and-class-information` directory variant and failed with `path_template_mismatch`. Query, fragment, and userinfo were absent. The allowlist was not changed and no second run was performed.
- Published no SEC source cache, observation, canonical evidence, or logical completion manifest. Staging residue was zero; the pre/post 34-file protected inventory remained 12,942,699 bytes with unchanged deterministic digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`. Existing identity, canonical EOD, and Massive evidence data were unchanged.
- Retained only the sanitized 3,903-byte failed diagnostic (`9abd62a6ef9dc4f61e41b6e32c9dde54b594d33dbf8b640c5673b764ede05c50`). No credential value, raw response, production snapshot/bundle, deployment, Universe activation, or OCI access occurred.

- Reconciled repository status documentation against current code, Git history, read-only `/data` metadata, completed logical manifests, and the SEC run audits. Corrected stale claims that real Massive ingestion, canonical EOD persistence, private analytics/Dashboard APIs, static Dashboard publication, and deployment tooling were absent.
- Recorded the last known OCI deployment strictly as Git/documentation history; OCI was not accessed and current live health was not asserted. Recorded ignored build/dist/snapshot/bundle artifacts, the open retention policy, undocumented `/data` child group-write policy, and the non-overwriteable `accepted_with_provenance_exception` 2026-08-14 identity snapshot.
- Clarified Event Engine design history in ADR 0004 and the Event Layer document: `Subject` is a Domain Object; `Observation` is a possible processing stage but not a core Domain Object; `Candidate` is temporary; `Event` is validated behavior; `Knowledge` is durable learning; full implementation remains deferred. This is distinct from SEC `SecEvidenceSubject`.
- Revalidated the documentation-only change with the offline backend, SEC, bulk-discovery, frontend, build, compile/import/health, shell syntax, Markdown-link, network-prohibition, and sensitive-information checks recorded in Current Status. No provider request, credential read, `/data` write, OCI access, snapshot/bundle generation, deployment, or artifact deletion occurred.

### SEC diagnostic remediation history

- Added landing-discovery diagnostic schema `2.0` with candidate/table/row ordinals, parsed year/date, bounded Size, public path structure, selection state, and finite URL rejection codes while retaining the compatible top-level `href_rejected` reason.
- Preserved all Series/Class, CEF, and BDC URL allowlists and selection semantics. Query, fragment, userinfo, external-host, raw HTML, headers, User-Agent, and contact values remain excluded from diagnostics. This offline work made zero network requests and did not access credentials, `/data`, OCI, snapshots, bundles, or deployment.
- Disabled retries specifically for the bounded SEC evidence live entrypoint and added a transport regression proving a recoverable first failure makes one request with zero retries; other provider retry behavior was unchanged.
- Executed the single newly authorized SEC run with cutoff 2026-08-14: three requests, zero retries, then a fail-closed `href_rejected` result in Investment Company Series/Class landing discovery. CEF, BDC, CSV files, and submissions were not requested.
- Published no SEC source cache, observation, canonical evidence, or logical completion manifest. Staging was clean and the 34-file protected canonical/identity/provider-evidence inventory was unchanged; no Massive access, snapshot, bundle, OCI access, or deployment occurred.

- Reworked SEC dated-CSV discovery around the official multi-table `File / Format / Size` DOM shape, including anchor-tail dates, deterministic two-digit year expansion, historical-undated exclusions, exact per-dataset paths, and row-order independence.
- Replaced the collapsed discovery failure with bounded structural reason codes and counts, and limited `application/octet-stream` acceptance to an already selected, non-empty CSV with matching dataset headers.
- Added three minimal synthetic official-shape fixtures and offline network-prohibition regression coverage. No SEC/Massive request, credential or `/data` access, snapshot, OCI access, or deployment occurred; the production Legacy Liquid Screen remains unchanged.

- Replaced the SEC landing-page single-CSV assumption with deterministic table-row selection by dataset year and effective/update date, including cutoff filtering, tied-URL rejection, URL containment, candidate statistics, and multi-year offline fixtures.
- Ran the separately authorized dated-selection B2B attempt once: three SEC requests, zero retries, then a safe stop at the first landing-page discovery gate. No CSV/submissions download, completed cache/evidence, shadow audit, snapshot, production Universe change, or OCI deployment occurred.

- Added the bounded Phase B2B SEC streaming transport, atomic source-cache safety checks, safe submissions ZIP reader, observation/canonical Parquet layers, logical completion marker, and offline tests.
- The first authorized run made three SEC requests and zero retries. It failed closed at the first official-CSV landing-page discovery gate; no completed cache/evidence partition, production snapshot, Universe switch, or OCI deployment was produced.

- Added the offline SEC issuer-structure evidence boundary with immutable point-in-time contracts, authoritative evidence grades, stable identity reconciliation, filing cutoff, BDC state-machine rules, deterministic Core/Broad decisions, and atomic tmp-only Parquet persistence.
- Added a private SEC User-Agent loader and interactive workstation helper plus an HTTPS allowlist, redaction, serial two-request-per-second ceiling, and bounded retry policy. No real contact value was configured and no SEC/Massive request, `/data` write, snapshot, OCI deployment, or production Universe change occurred.

## 2026-08-16

- Executed the separately authorized corrected Phase B1B run: one Ticker Types request plus 14 point-in-time All Tickers pages, zero retries, and no other provider endpoint.
- Published a 25-code provider catalog, 13,110 normalized observations, 9,939 canonical evidence records, and a logical completion marker after schema/count/fingerprint/hash rereads. Reconciliation was 9,939 mapped plus 3,171 expected-unjoined with zero ambiguity, collision, malformed record, duplicate, or canonical conflict.
- Re-audited the unchanged legacy 1,864-member universe: 1,862 remain quarantine, VCX is the one authoritative exclusion, and AKAN is the one authoritative Broad candidate. Core remains 0 and Broad remains 1 because provider type does not establish issuer structure or domicile.
- Added logical completed-snapshot reads, a 99.9% linkage gate, exact request-attempt accounting, and nullable sanitized diagnostics for failures before reconciliation. Existing Instrument Master, identity, resolver, EOD, and legacy calculations were not modified.
- Deployed provisional disclosure release `2026-08-14T020535Z-ebb16015b7da` from clean source commit `ebb16015b7da259e68033ca442544def5a300d63`. The bundle retained the exact prior summary, movers, and Trading Activity Map payloads while adding the legacy/provisional label and material evidence warning.
- Verified root/login/dashboard/private-data/auth boundaries, remote checksums, active Nginx/Auth Service, localhost-only 8010, zero failed units, and no 8000/8001/5173 listener. No real user password was used.

## 2026-08-15

- Completed Phase B1A entirely offline. Read-only reconciliation found two duplicate-ticker groups (`BCPC`, `TPC`), each with one stable-ID resolved observation and one identifier-free excluded observation; old ticker fallback caused all four false ambiguities and a business-key conflict count of four.
- Split normalized Provider Security Observation V1 from canonical Provider Instrument Security Evidence V1, corrected linkage to 9,939/9,939 with 3,171 expected-unjoined observations, and added deterministic observation IDs plus canonical conflict handling.
- Added sanitized failed-run diagnostics outside completed evidence datasets. No Massive/SEC request, credential access, `/data` write, production snapshot, frontend deployment, or OCI access occurred.

- Selected Core U.S. Domestic Operating Equities as the future default and Broad U.S.-Listed Operating Equities as the future secondary view; production activation remains deferred.
- Implemented provider ticker-type catalog and point-in-time instrument security evidence contracts, bounded Massive ingestion, atomic Parquet persistence, and provisional Dashboard governance metadata.
- Ran one authorized Phase B1 sequence: 1 Ticker Types request plus 14 All Tickers pages, zero retries. The 13,110 raw records reconciled, but four ambiguous mappings, nonzero mapped business-key conflicts, and an initially incorrect identity-link denominator failed hard gates.
- Published no evidence partition, generated no production snapshot, and made no OCI deployment. Corrected the identity-link denominator and retained the production stop pending a separately authorized rerun.

- Accepted ADR 0015 and implemented provider-neutral, effective-dated Security Classification V1 with separate security form, issuer structure, listing scope, evidence, status, and disposition.
- Completed the read-only Phase A audit: 9,939 Instrument Master records, 9,889 comparable records, 5,360 explicit ETFs, 4,527 unknown/quarantined non-ETF records, one excluded VCX closed-end fund, and one Broad candidate AKAN foreign ordinary share.
- Computed non-production Phase A Core and Broad candidates of 0 and 1. Production remains on the legacy 1,864-member universe pending evidence remediation; the later product-policy decision does not make these evidence-limited counts production-ready.
- Added deterministic contract, override, point-in-time, reconciliation, funnel, and pollution tests. No Massive call, credential access, `/data` modification, snapshot generation, frontend change, or OCI deployment occurred.

- Accepted the integrity-verified 2026-08-14 Instrument Master, provider identity, and ticker resolver logical snapshot as `accepted_with_provenance_exception`; original request and pagination provenance remains unknown, and the snapshot must not be requested again or overwritten.
- Accepted ADR 0014 and implemented an offline XNYS market-session calendar with injectable time, expected-versus-actual session lag, and separate file-consistency and calendar-freshness statuses.
- Executed exactly one authorized Massive Grouped Daily request for 2026-08-14 with `adjusted=false` and no retry; all hard gates passed and 9,912 canonical EOD bars were published without raw payload persistence.
- Generated a current 2026-08-14 / previous 2026-08-13 private snapshot with XNYS lag zero and freshness `fresh`, then deployed release `2026-08-14T224306Z-21d0e7fda749` from source commit `21d0e7fda749e3afec7edc9a884eb6408663004f`.
- Verified root login, compatibility redirect, unauthenticated Dashboard redirect, private-data/status protection, external internal-auth denial, remote checksums, active services, and localhost-only Auth listener. No authentication credential or policy changed.

- Upgraded Dashboard V1.1 Market Overview with SPY/QQQ/IWM/DIA benchmark strip, equal-weight universe benchmark, Sector ETF relative-to-SPY performance, conservative data freshness wording, top-50 Trading Activity Map default, improved map labels/search/detail panel, and categorized Data Details.
- Completed read-only SNDK review against canonical 2026-08-12 and 2026-08-13 data: identity and OHLC are internally consistent, but corporate-action/adjustment evidence is insufficient; canonical `/data` was not modified.
- Did not call Massive, read Massive credentials, modify `/data`, change authentication/password/session behavior, or alter market-data canonical partitions.
- Deployed private Dashboard Market Overview release `2026-08-13T214820Z-32fed3a8b17b` from source commit `32fed3a8b17b020e00c33f839d2a12e9de50d855`; unauthenticated root/login/dashboard/private-data protection checks passed.

- Recorded user-completed production acceptance for root session login, Dashboard data loading, Logout, and WH Alpha password rotation without recording any password or hash.
- Accepted ADR 0013 and implemented Dashboard V1.1 professional universe cleanup with `Tradable U.S. Equities` as the default view.
- Added Sector Benchmark ETFs as a separate fixed benchmark module and renamed the filtered treemap UI to Trading Activity Map.
- Moved broad engineering/session details into collapsible Data Details and categorized quality flags instead of showing a single large warning count.

- Repaired the OCI password rotation helper after the first real run failed during immediate listener verification; current password version is marked unknown until the user reruns the repaired interactive rotation.
- Hardened listener parsing, bounded readiness polling, and post-replacement rollback status output; password minimum is now a hard 10 characters with longer unique passwords recommended.

- Deployed root-login release `2026-08-13T135949Z-92819ed17316` from source commit `92819ed17316c567c40b440f5c2e8487f9db4b53`; made `https://whalpha.com/` the official branded WH Alpha session-login entry and changed `/login/` to a compatibility redirect to `/`.
- Added a minimal `/auth/status` check for root-entry session detection; it returns only 204 or 401 with no session details.
- Updated Dashboard unauthenticated redirects to `/?next=/dashboard/` while keeping `/private-data/` protected with 401 JSON.
- Added and deployed the OCI-only password rotation helper for interactive user-run rotation; it does not accept or print passwords or hashes.
- Did not call Massive, read Massive credentials, modify `/data`, or change Dashboard analytics, numeric formatting, or Liquidity Map behavior.

- Fixed the production login form submission contract so Sign In uses same-origin JSON `POST /auth/login` instead of native navigation; deployed release `2026-08-15T133119Z-137f244e8508`.
- Repaired the OCI `/login/` route verification by mapping the login path explicitly to the release artifact and requiring branded-login body markers during deployment; deployed release `2026-08-15T130949Z-78eedc071786`.
- Deployed private Dashboard session-login release `2026-08-15T125517Z-0fa5cac89847` and replaced browser-native Basic Auth with a branded `/login/` page and localhost-only server-side session Auth Service.
- Added secure session cookies, logout, wrong-password safe failure behavior, and Nginx `auth_request` protection for `/dashboard/` and `/private-data/`.
- Fixed Dashboard presentation formatting for long Decimal ratios, percentages, compact volume, compact currency, and metric/card overflow.
- Did not read or output the Dashboard password/hash, call Massive, read Massive credentials, modify `/data`, or change Liquidity Map algorithms.

- Provisioned a dedicated `dell5820` to OCI deployment SSH key while retaining the existing WSL OCI key.
- Regenerated the private Dashboard snapshot and OCI bundle from clean source commit `987b5289a7835316ef6aae4aa326aff46de58896`.
- Deployed private Dashboard release `2026-08-13T120220Z-987b5289a783` to OCI as the initial Basic Auth-protected release; it was later superseded by the session-login release.
- Verified public `/` remains the data-free placeholder and unauthenticated `/dashboard/` plus `/private-data/v1/manifest.json` return 401.
- Did not read or output the Dashboard password/hash, call Massive, read Massive credentials, modify `/data`, deploy raw/Parquet data, or access another OCI instance.

- Accepted ADR 0011 for authenticated static private dashboard snapshots.
- Implemented the private Dashboard JSON snapshot exporter and manifest/hash validation.
- Added frontend `snapshot` mode for `/dashboard/` static deployment and `/private-data/` JSON snapshots.
- Added a versioned OCI dashboard bundle builder, Nginx template, dry-run deployment script, and private access runbook.
- Completed read-only OCI preflight without creating credentials, uploading files, reloading Nginx, modifying whalpha.com, accessing Massive, or changing `/data`.

- Implemented the first local React Market Dashboard V1 using the private Market Summary, Movers, and Liquidity Map APIs.
- Added explicit API and synthetic demo modes; API mode does not fall back to demo fixtures on failure.
- Rendered Market Pulse, Market Breadth, Up/Down Volume, liquidity-screened movers, Liquidity Map V1, and Data Quality / Session Metadata.
- Added frontend unit/component tests with Vitest, React Testing Library, jsdom, and mocked ECharts initialization/disposal.
- Verified frontend production build locally; no Massive request, credential access, `/data` write, OCI access, or deployment was introduced.

- Published the 2026-08-12 Massive Instrument Master, provider identity, provider ticker resolver, and canonical EOD Price Bar datasets through the existing bounded pipelines.
- Implemented provider-neutral close-to-close EOD return analytics across the completed 2026-08-12 and 2026-08-13 sessions.
- Added Market Summary V1, liquidity-screened movers, paginated returns, and Liquidity Map V1 private API response contracts.
- Documented that Liquidity Map V1 is not market-cap weighted, not sector grouped, and not a fund-flow or money-flow map.
- No frontend change, OCI access, deployment, database, raw payload persistence, or system service change was introduced.


- Implemented the first canonical EOD read repository for completed Parquet sessions with manifest, schema, fingerprint, and identity snapshot validation.
- Added a paginated provider-neutral EOD query service and private FastAPI response contracts with Decimal values serialized as strings.
- Added default-disabled private EOD market-data routes gated by `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES`; default OpenAPI does not show the private routes.
- Verified the completed 2026-08-13 production session read path locally without modifying `/data`, reading credentials, calling Massive, changing frontend code, or deploying OCI.

## 2026-08-14

- Accepted ADR 0010 to represent aggregate EOD volume as exact non-negative Decimal while keeping trade count and timestamps integer-semantic.
- Updated EOD Price Bar V1, Massive mapping, Grouped Daily inspection/ingestion, Arrow schema, Parquet persistence, fingerprints, and tests for Decimal volume.
- Re-ran the authorized 2026-08-13 Massive Grouped Daily request once with `adjusted=false`; all V1 gates passed and 9,901 canonical EOD bars were published.
- Recorded 11,208 fractional-volume records, 4 isolated conflicting duplicate records, 4 missing optional VWAP values, 4 missing optional trade-count values, and 4 zero-volume records as quality warnings.
- No raw provider payload, Dashboard data flow, OCI access, database, scheduler, or system change was introduced.

- Hardened Massive Grouped Daily numeric parsing for JSON int, finite float, Decimal, and numeric string inputs while rejecting bool, non-finite values, malformed strings, and fractional integer-semantic fields.
- Fixed Grouped Daily processing so identity classification is counted before numeric validation and remains independent from OHLCV parse failures.
- Changed low-ratio conflicting duplicate bars from a hard session failure to isolated quality warnings, while preserving a hard gate above the accepted ratio.
- Re-ran the authorized 2026-08-13 Grouped Daily request once; identity coverage passed, but numeric conversion failures and canonical bar count gates blocked publication.
- No raw payload, EOD Parquet partition, Dashboard data flow, OCI access, or system change was introduced.

- Added a controlled Massive Grouped Daily publication entrypoint for the completed 2026-08-13 session using the completed point-in-time ticker resolver.
- Executed one authorized Grouped Daily request with `adjusted=false`; access succeeded but quality gates blocked publication.
- Recorded conflicting duplicate bars, numeric conversion failures, low identity coverage, and insufficient canonical bar count as the exact blockers.
- No raw payload, EOD Parquet partition, Dashboard data flow, OCI access, or system change was introduced.

- Refined Massive Instrument Master snapshot quality classification to separate eligible records, expected exclusions, malformed records, ticker ambiguity, and stable-ID collisions.
- Added Provider Ticker Resolver V1 and included it in the logical Instrument Master snapshot completion marker.
- Re-ran the authorized 2026-08-13 Massive All Tickers pagination once; corrected quality gates passed and published 9,932 canonical instruments, 13,106 provider identity records, and 9,932 resolver entries.
- No raw Massive payload, Grouped Daily call, Dashboard data flow, OCI access, or system change was introduced.

- Added Provider Instrument Identity V1 as a Python contract and data-contract document.
- Accepted ADR 0009 for stable provider identifiers and deterministic UUIDv5 canonical instrument identity.
- Implemented bounded Massive All Tickers point-in-time Instrument Master snapshot ingestion with fixed-interval pagination.
- Implemented Instrument Master and provider identity Parquet snapshot repositories with logical completion marker semantics.
- Executed one live Massive All Tickers snapshot attempt for 2026-08-13; pagination completed, but quality gates blocked publication.
- No raw provider payload, completed Instrument Master snapshot, Grouped Daily publication, Dashboard data flow, OCI access, or system change was introduced.

- Added a safe one-request Massive Grouped Daily inspection tool.
- Executed one read-only Grouped Daily inspection for 2026-08-13 with `adjusted=false`.
- Verified Grouped Daily access and payload structure without saving raw or canonical data.
- Confirmed production publication is blocked pending Instrument Master identity coverage.
- No Parquet write, `/data` write, repository publish, second Massive request, Dashboard data flow, OCI access, or provider-backed deployment was introduced.
- Accepted partitioned Parquet as the initial canonical EOD Price Bar persistence format.
- Implemented a one-session provider-neutral EOD ingestion service for mocked fixtures.
- Implemented an explicit PyArrow EOD Price Bar V1 Parquet repository, manifest, deterministic content fingerprint, atomic publish, idempotency, and conflict/corruption checks.
- Added mocked-fixture ingestion and Parquet persistence tests.
- No Massive API call, credential access, production `/data` write, scheduler, historical backfill, analytics, database, Dashboard API, or OCI deployment was introduced.
- Implemented the protected Massive credential-file loader.
- Implemented a minimal standard-library HTTPS transport using Authorization bearer headers.
- Added local security tests for credential parsing, transport behavior, error mapping, redirect handling, and network prohibition.
- Verified one read-only Massive Stocks reference smoke test without outputting raw data or credentials.
- No ingestion, Grouped Daily download, persistence, Dashboard data flow, OCI deployment, or public provider-backed access was introduced.
- Implemented the Massive Stocks configuration and credential boundary.
- Added a mocked-only Massive adapter skeleton for Instrument Master and EOD Price Bars.
- Added deterministic mocked HTTP response tests for Massive mapping, error handling, pagination, and credential redaction.
- No real API key, Massive API call, market-data download, persistence, provider-backed deployment, or access-control change was introduced.
- Evaluated Massive Stocks Basic using official public documentation.
- Accepted Massive Stocks Basic as the first private EOD development provider.
- Documented public-display and Derived Works restrictions for provider-backed data.
- Accepted the public placeholder, public data-free demo, and private real-data dashboard boundary.
- No account, credential, adapter, API request, data ingestion, deployment, or access-control change was introduced.
- Implemented the synchronous provider-neutral MarketDataProvider Protocol.
- Added provider capabilities and query models for Instrument Master and EOD Price Bars.
- Added explicit provider error taxonomy.
- Added deterministic in-memory provider contract test fake.
- No real provider, network access, credentials, ingestion, persistence, database, or Dashboard implementation was introduced.

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

# Roadmap

- Next operational step: continue the Dell-only daily pipeline optimization
  after the verified Candidate append and Phase 1b stable-prefix correction:
  verified-prior Phase 1b append, immutable panel-stage reuse, and streaming/
  resumable Candidate audit output, explicit validation tiers, and bounded
  deterministic cold-Oracle process parallelism are complete. The exact-
  session read-only planner plus single-action offline executor and durable
  Dell run custody plus the network-free session-readiness, bounded retry, and
  missed-session policy and durable acquisition-attempt custody are complete
  in repository source. The default-deny, expiring standing-authorization
  boundary for provider acquisition/canonical apply is also defined and
  repository-tested but not activated. The one-transition coordinator core is
  complete with default-absent provider/apply capabilities, and canonical
  Apply reservation/recovery custody is complete under journal 1.2. ADR 0036
  capability adapters now compose the real boundaries while remaining
  uninstalled and inactive. The default-disabled externally pinned host config
  and one-transition CLI are now repository-tested. Exact one-event recovery
  routing is also complete for acquisition, canonical Apply, and offline
  actions without request, Apply, replay, or loop. The channel-neutral alert
  intent and deterministic deduplication identity are also complete. Keep
  manual approval while code revision is still changing. At-most-once alert
  delivery custody and its default-disabled, externally configured SMTP adapter
  are complete in repository source. The network-prohibited joint preflight for
  external alert/host/data-authorization artifacts is also repository-tested.
  Explicit post-coordination intent/custody/SMTP composition is complete under
  a default-off CLI flag. External preflight 1.1 now also supports explicit
  `daily_data_only` review while SMTP remains deferred. Its first controlled
  run completed same-day Identity but the one EOD request failed permanently
  before a package existed. ADR 0045 now preserves safe status/request evidence
  for future attempts. ADR 0047 makes readiness plan-aware and adds a bounded,
  immutable operator-review path without changing the old unknown HTTP status.
  One real offline review binds that terminal to a conservative
  2026-08-28T16:00:00Z boundary without authorizing a retry. Recheck readiness
  only at or after that time before any retry or scheduler consideration.
  Publication, Snapshot, bundle, and OCI remain separate authorizations.
- Next product-validation step: review the implemented additive Candidate
  consumer that presents leadership quality and entry location as separate
  axes with review-now, watch-trigger, wait-reset, and other lanes.
  Do not tune the frozen shadow thresholds from the one-session distribution;
  review them chronologically when enough history exists.
  The bilingual hierarchy, Daily Decision Brief, current-payload change layer,
  relationship decision lanes, and equal-capability guest Session entry are
  implemented in repository source. Exact relationship run length/acceleration,
  formal taxonomy, and position management remain separate contract work.
  ADR 0048 and Snapshot 1.8 / Dashboard 2.5 now split the 20.4 MB Candidate
  payload into a 1.49 MB first-load summary and 32 on-demand detail shards while
  formally reconstructing the unchanged full publication. ADR 0049 now defines
  the independent six-channel shadow taxonomy and evidence rules without a
  formula or Production integration. The next model step is a point-in-time
  chronological evaluation panel before any score or threshold is selected.
  ADR 0050 now fixes its sealed-signal/later-outcome and anti-leakage contract;
  the read-only historical audit is complete and returns
  `NOT_READY_FOR_PERFORMANCE_EVALUATION`. ADR 0051 and Historical Research Data
  Foundation V1 now complete the source-neutral retention design for daily
  membership, corporate actions/lifecycle, adjustment reconciliation, and the
  252/504-session boundary. The current public provider review and Dell
  storage/request plan are also complete. Provider-neutral historical row and
  coverage contracts now enforce the point-in-time boundary with synthetic
  tests, and the four new row families have explicit temporary-root Parquet
  writers/readers with immutable completion evidence. The next repository-safe
  step has also completed saved synthetic split/dividend response mapping,
  independent Decimal adjustment invariants, and the credential-free read-only
  exact pilot planner. Real provider work remains blocked on permission/product
  posture, entitlement, lifecycle-source review, and exact authorization.

This roadmap is a proposed sequence, not a commitment or date plan.

## Phase 0 — Foundation

- [x] Infrastructure audit and cleanup
- [x] Access normalization
- [x] Documentation bootstrap
- [x] Storage preparation
- [x] Application technology stack decision
- [x] Target application architecture documentation

## Phase 1 — Market Dashboard MVP

- [x] Minimal application scaffold
- [x] Local frontend/backend development toolchain
- [x] Define Initial EOD Universe
- [x] Define Sector/Industry, Theme, and Analytical Group boundary
- [x] Define normalized EOD logical contracts
- [x] Instrument Master V1 model and validation tests
- [x] EOD Price Bar V1 model and validation tests
- [ ] Remaining logical contract models
- [x] Minimal provider boundary Protocol
- [x] Deterministic in-memory provider contract tests
- [x] First real EOD provider evaluation
- [x] Massive adapter configuration and credential boundary with mocked HTTP responses
- [x] Massive account entitlement and secure credential provisioning smoke test
- [x] First bounded EOD ingestion slice with mocked fixtures
- [x] Separately authorized one-session Grouped Daily inspection without publication
- [x] Point-in-time Massive Instrument Master snapshot ingestion path
- [x] Instrument Master snapshot quality-gate remediation and publication
- [x] Grouped Daily parser, identity-ordering, and duplicate-isolation remediation
- [x] Decimal aggregate-volume correction and first canonical EOD session publication
- [x] Private canonical EOD read/query API for the completed 2026-08-13 session
- [x] 2026-08-12 bounded ingestion and first close-to-close Market Summary analytics
- [x] Bounded real-provider identity and EOD ingestion workflows
- [x] Approval-bound same-day fetch/plan/apply/reread workflow with offline
  apply, same-day Identity dependency, recovery, and fake-transport rehearsal
- [x] Initial three-session EOD development dataset
- [x] Initial close-to-close market summary, breadth, movers, benchmark, and trading-activity calculations
- [x] Local React Market Dashboard V1 shell
- [x] Liquidity Map V1 treemap
- [x] EOD breadth and up/down volume views
- [x] Private static dashboard snapshot exporter and OCI bundle package

- [ ] Rotation
- [x] Fixed registered ETF relationship monitor
- [ ] Lightweight developments
- [x] First usable private static deployment
- [x] Dashboard V1.1 professional universe and market overview cleanup
- [x] Dashboard V1.1 trust/usability pass with benchmark strip, Sector ETF relative performance, conservative freshness, and top-50 Trading Activity Map default
- [x] Provider-neutral offline XNYS market-session calendar and explicit freshness contract
- [x] Corrected Phase B1 provider security-type evidence publication and provisional universe disclosure source
- [x] Offline SEC issuer-structure evidence boundary, private User-Agent tool, fixture state machines, and tmp-only persistence
- [x] Bounded SEC live transport, source-cache/evidence publication boundaries, two-stage selected-source discovery gate, and diagnostic schema `3.0` with historical schema `2.0` audit compatibility
- [x] Exact nine-artifact private SEC source-cache reconciliation and hardened submissions ZIP validation
- [ ] Successful SEC issuer-structure evidence publication and Core/Broad activation review — paused for the current product stage after the final bounded run failed closed
- [x] Offline Provider-Classified Common Shares (CS-only) and CS+ADRC shadow audit with stable-ID reconciliation and deterministic fingerprints
- [x] Provider-neutral 20-session XNYS history planner, bounded canonical reader, Decimal trailing-liquidity contract, readiness audit, and offline backfill plan
- [x] Successful 2026-07-17 same-day identity plus Grouped Daily single-session production backfill pilot
- [x] Successful first three-session production backfill batch for 2026-07-20 through 2026-07-22
- [x] Successful second three-session production backfill batch for 2026-07-23, 2026-07-24, and 2026-07-27
- [x] Successful third three-session production backfill batch for 2026-07-28 through 2026-07-30
- [x] Successful fourth three-session production backfill batch for 2026-07-31, 2026-08-03, and 2026-08-04
- [x] Successful fifth three-session production backfill batch for 2026-08-05 through 2026-08-07
- [x] Successful final two-session production backfill batch for 2026-08-10 and 2026-08-11; 20-session partition descriptor ready
- [x] Calendar-bounded latest EOD catch-up for 2026-08-17 through 2026-08-19; canonical freshness lag zero
- [x] Versioned Trailing Liquidity V1 metric/decision shadow publication for 2026-08-19 with logical completion marker
- [x] Stable-ID Legacy/A/B pre-activation comparison and Reviewed Eligibility Override V1 shadow publication
- [x] Versioned Dashboard Universe Activation V1 with selectable Common Shares and Common Shares + ADRs
- [x] Multi-Universe private API, snapshot, and React selector integration
- [x] Market Regime & Opportunity Map V1 product, quantitative, data-contract,
  architecture, validation, and phased-delivery design
- [x] Market Regime Phase 1a offline raw-metric and five-dimension ledger
- [x] Market Regime Phase 1b offline state/hysteresis ledger
- [x] Market Regime Phase 2 offline fixed-basket ETF Relationship Map
- [x] Market Regime read-only local API, preview bundle, and first React page
- [x] Typed English/Simplified Chinese interface for login, Dashboard, and
  Market Regime in local and private static production modes
- [x] Market Intelligence immutable contract, reader, publisher, Snapshot 1.5,
  and explicit OCI integration path
- [x] Exact, one-release stale review authorization contract and bilingual
  `stale_review` presentation without weakening normal freshness
- [x] Immutable 2026-08-24 Market Intelligence production publication
- [x] Snapshot 1.5 / Dashboard 2.2 stale-review publication and bound OCI bundle
- [x] Production bundle isolation from synthetic Dashboard fixtures
- [x] Persistent first-level workspace navigation, shared Universe/language/
  Session controls, factual first-screen market summary, six relationship
  highlights, sticky-header isolation, and Universe/comparable explanation
- [x] Daily Decision Brief, one-/five-session Regime changes, two-sided
  threshold distance, economic-lane relationship highlights, prior-state
  change markers, consolidated reliability warning, and collapsed audit table
- [x] Equal-capability guest Session entry with the same protected payload and
  no role-dependent product branch
- [x] Phase 5 Candidate score/risk/state, independent Oracle, and canonical audit
- [x] Bounded Candidate publication, MI 1.1, Snapshot 1.6 / Dashboard 2.3, and
  deployed bilingual first-level Stock Candidate workspace
- [x] Offline Candidate Entry Geometry V1 contract, fixed parameters,
  independent Oracle, canonical audit, and real-data chase-bias review
- [x] Additive Candidate entry-geometry publication/Snapshot/frontend consumer
- [x] Freshness-compliant MI 1.2 / Snapshot 1.7 / Dashboard 2.4 publication,
  bundle, and separately approved OCI deployment
- [x] Candidate full-path stage measurement, overlapping-panel shared reads,
  stable-ID state indexing, and worktree-safe Dell Python runner
- [x] Verified-prior Candidate incremental state with corrected cold-output equivalence
- [x] Verified-prior Phase 1b incremental state with cold business-output equivalence
- [x] Immutable formally validated Phase 1a/Candidate panel-stage reuse
- [x] Streaming and resumable source-bound Candidate audit stages
- [x] Candidate daily/periodic/code-change validation tiers
- [x] Deterministic cold-replay Candidate Oracle process parallelism with serial equivalence
- [x] Exact-session daily planner and single-action offline executor with durable run custody
- [x] XNYS-close-aware readiness, bounded retry, alert state, and oldest-gap recovery policy
- [x] Shared-lock durable provider-attempt reservation, outcome, and recovery custody
- [x] Expiring, externally SHA-pinned standing Identity/EOD data-authorization contract
- [x] Default-deny one-transition coordinator core with explicit capability ports
- [x] Canonical Identity/EOD Apply reservation and no-write interruption recovery
- [x] Standing-authorized fetch/Apply capability composition with exact request counts
- [x] Externally SHA-pinned host runtime and default-disabled one-transition CLI
- [x] Exact one-transition recovery routing without request, Apply, or replay
- [x] Channel-neutral daily alert intent with stable deduplication identity
- [x] Immutable at-most-once alert delivery custody with ambiguous replay stop
- [x] Default-disabled external SMTP adapter with owner-only credential custody
- [x] Network-prohibited joint external-control configuration preflight
- [x] Explicit post-coordination email delivery composition with at-most-once custody
- [x] Explicit data-only external preflight while SMTP remains deferred
- [x] Safe provider failure status and request-count evidence
- [x] Context report separates latest Identity from EOD-bound Identity
- [x] Plan-aware Basic EOD readiness and immutable single-use operator review
- [x] Lossless Candidate summary/on-demand-detail Snapshot projection
- [x] Independent Candidate strategy-channel shadow taxonomy and contract
- [x] Sealed-signal/later-outcome chronological evaluation contract
- [x] Read-only historical strategy-evaluation readiness audit
- [x] Point-in-time historical research foundation and source capability gap matrix
- [x] Provider-neutral historical row and coverage/readiness contracts
- [x] Historical PyArrow schemas and temporary-root Parquet repositories
- [x] Synthetic Massive split/dividend mapping and adjustment invariants
- [x] Credential-free read-only exact historical pilot planner
- [x] Cross-family Data Record Governance V1 and equal-capability serving policy
- [x] Default-deny historical Pilot approval-review package
- [x] Official equal-capability multi-source review and use-specific source-permission governance

## Next Small Target

Keep the 2026-08-27 EOD attempt paused until its immutable
2026-08-28T16:00:00Z boundary. The offline review does not authorize a retry
after that time, and the old exact-revision controls remain inactive. Product
development may continue from the formally completed 2026-08-26 inputs.

ADR 0051, Historical Research Data Foundation V1, and the repository-evidenced
source capability matrix are complete. The 2026-08-28 official-source review
and physical storage/request plan are also complete and return
`NOT_READY_FOR_PROVIDER_PILOT_AUTHORIZATION`: equal-capability guest use is not
compatible with the documented owner-only terms, owner non-display/derived use
needs clarification, live historical/corporate-action entitlement is
unverified, and full lifecycle sources are absent.

The credential-free read-only pilot planner is complete: it binds exact
requested sessions and caller inventory, endpoint/page ceilings, deterministic
future `/tmp` paths, source gaps, and a permanent default-deny result. The
approval-review boundary is also complete and selects 2026-07-14 through
2026-07-16 as the deterministic preliminary window with a 75-request ceiling
and no unnamed Ticker Events. Re-review equal-capability source permission,
account endpoint entitlement, missing lifecycle sources, and a fresh exact
inventory before one exact live-pilot authorization. Product
posture is no longer open: guest and credential shared content stay identical,
and owner-only market analysis is not a fallback.
Do not access credentials, acquire, or write history before those gates clear.
Do not select formulas or thresholds from one-session distributions. Keep
Snapshot 1.8 undeployed until its exact bundle and browser behavior are
separately reviewed. Keep SMTP and SEC B2 paused.

The next historical-foundation implementation target is not another provider
adapter. Pilot approval 1.1 is now bound to fresh exact source-permission
assessments, and the durable fixture-only permission-review repository is
complete. Next obtain written candidate-plan answers and publish a real review
package only under separate exact authorization; only a separately authorized
pilot may follow. SEC/GLEIF/OpenFIGI
fixture adapters can be designed independently afterward, without treating
their open identifiers or filings as complete security/lifecycle evidence.

## Phase 2 — Intraday and Options

- [ ] Delayed/intraday upgrades
- [ ] Selected Options structure
- [ ] Scheduling and reliability
- [ ] Stronger monitoring

## Later

- Portfolio
- Richer Event workflows
- Formal multi-user authentication beyond the personal-prototype session boundary
- AI explanation
- Broader public showcase

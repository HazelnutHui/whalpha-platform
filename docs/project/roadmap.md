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
  delivery custody is complete with no transport installed. Next implement one
  externally configured email adapter, then review external authorization,
  controlled rehearsal, and scheduler activation separately. Publication,
  Snapshot, bundle, and OCI remain separate authorizations.
- Next product-validation step: review the implemented additive Candidate
  consumer that presents leadership quality and entry location as separate
  axes with review-now, watch-trigger, wait-reset, and other lanes.
  Do not tune the frozen shadow thresholds from the one-session distribution;
  review them chronologically when enough history exists.
  The bilingual hierarchy, Daily Decision Brief, current-payload change layer,
  relationship decision lanes, and equal-capability guest Session entry are
  implemented in repository source. Exact relationship run length/acceleration,
  formal taxonomy, and position management remain separate contract work.

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

## Next Small Target

Implement one externally configured email transport behind the completed alert
custody boundary without placing channel credentials in Git. Then review
external host/authorization artifacts at the stable implementation revision
and conduct a controlled one-transition rehearsal before considering scheduler
activation. Do not combine Production publication, Snapshot, bundle, OCI, or
deployment authorization. Keep SEC B2 paused.

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

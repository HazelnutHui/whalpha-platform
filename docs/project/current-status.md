# Current Status

Status date: 2026-08-28

This document is the concise current-state summary. Exact publication IDs,
fingerprints, verification scope, and cross-device handoff are maintained in
the [authoritative current context](current-context.md). Historical execution
detail belongs in the [changelog](changelog.md) and dated audits, not here.

## Current product

WH Alpha is a Session-protected, bilingual U.S. equity market-intelligence
dashboard for discretionary research. Its intended decision chain is:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

The current production-capable source slice covers market overview, breadth, movers,
Trading Activity Map, benchmark and sector-ETF context, a transparent five-
dimension Market Regime, 16 preregistered ETF relationships, and a bounded
Stock Candidate research workspace. English is
the first-visit default; English and Simplified Chinese render the same
language-neutral analytics.

Repository source now presents Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, and Stock Candidates
(`个股候选`) as first-level workspaces with persistent desktop
left navigation and one shared Universe/language/Session utility header. Market
Regime & Opportunities is the first item and default workspace; Market
Structure & Activity is second and begins with a factual “what is happening
now” summary.
It explains Universe membership versus same-session comparable coverage. A
Daily Decision Brief adds one- and five-session Composite changes, distances
to both state boundaries, and an explicit broad Risk-on stance. Six fixed
economic decision lanes precede the collapsed complete 16-pair audit table;
each highlight shows current-versus-prior relationship state, and the short-
history warning is consolidated. These changes and equal-capability guest entry
are deployed in the current OCI release.

The interface supports human decisions. It does not issue orders, model option
returns, or claim causality. Price and volume analytics are participation or
relative-performance proxies, never actual fund flow.

## Active data and publications

- Canonical EOD is completed through 2026-08-26; latest canonical Identity is
  2026-08-27, so Identity is one session ahead of EOD.
- Latest EOD contains 9,953 rows. Latest Identity contains 9,982 canonical
  instruments, 13,148 provider observations, and 9,982 resolver rows. The
  Identity snapshot bound to latest EOD remains 2026-08-26 with 9,974 / 13,141
  / 9,974 rows respectively.
- Activation V2 is active with Common Shares as the sole default:
  - Primary: 1,718 CS.
  - Secondary: 1,831 = 1,718 CS + 113 ADRC.
- Active Market Intelligence publication is
  `2026-08-26T050254Z-6c60502e4473`, contract 1.2, with 496 Primary and 532
  Secondary bounded Candidate research records across the fixed entry lanes.
- Active Dashboard Snapshot is
  `2026-08-26T053233Z-6c60502e4473`, contract 1.7 / Dashboard 2.4.
- The locally retained OCI bundle and live-verified deployed release are
  `2026-08-26T053233Z-6c60502e4473` from source commit `6c60502e4473`.

The active analytics and Snapshot were published as the ordinary fresh
2026-08-26 release: expected and actual session were both 2026-08-26, lag was
zero, data status was `complete`, and review mode was false. After the
2026-08-27 close, canonical EOD now lags the expected session by one because
the controlled EOD request failed. No new analytics or Snapshot was published,
and the static active payload does not dynamically rewrite its publication-
time freshness metadata. The prior narrowly bound 2026-08-24 `stale_review`
release remains historical evidence only; it did not weaken the normal gate.

The exact failed EOD terminal now has one immutable offline operator review.
The current readiness state is `waiting_to_retry` until
2026-08-28T16:00:00Z, with one attempt, one review, no alert, zero external
requests, and zero Production writes in the review decision. This boundary is
a conservative operator choice, not a verified REST release time. It grants
no provider-fetch authority; the old exact-revision Host Runtime and standing
authorization are inactive after later commits.

## Market Regime

- Primary: 57.8456, Balanced.
- Secondary: 57.9041, Balanced.
- Fixed basket: 30 ETFs.
- Preregistered relationships: 16.
- Windows: 5, 10, and 20 XNYS sessions.
- Relationship-history rows: 336.
- History depth: 26 sessions, so relationship confidence remains low and is
  implementation evidence rather than predictive validation.

The underlying active publication was formally reread after the 2026-08-27
deployment. Exact displayed scores are publication facts, not trade signals.

## Access and deployment boundary

- `/` is the branded credential-or-guest Session entry.
- `/dashboard/` and `/private-data/` share the server-side Session boundary.
- The Auth Service design is localhost-only on OCI.
- Production bundles contain no canonical Parquet, raw provider payload, or
  credentials.
- Synthetic Dashboard data is excluded from the production dependency graph.
  API and Snapshot failures fail closed and never fall back to demo data.
- Guest entry creates the same role-free opaque Session as credential login.
  Guest and credential Sessions expose the same data, functionality, language,
  Universe, precision, freshness, and analytics. No role-based difference is
  authorized.
- The user has reaffirmed that this is a hard shared-product rule. Source
  incompatibility must be resolved through permission or replacement, not an
  owner-only market-analysis tier. Future personal records require a separate
  identity boundary and do not change shared analytics parity.

The 2026-08-27 deployment passed remote preflight, Nginx configuration checks,
atomic apply, unauthenticated protection, and the temporary equal-capability
guest Session postflight defined by the deployment tool. Password-based and
visual browser behavior remains a manual user check because no password was
read or used.

## Current limitations and risks

- The active static 2026-08-26 payload still carries its publication-time
  `complete` metadata even though the post-close 2026-08-27 pipeline is now one
  session behind. No later stale-review or fresh release was published; users
  must rely on the displayed analysis/session date until the daily chain is
  repaired.
- The analytics history is only 29 EOD sessions and the active calculations
  use 26 sessions. This is contract and implementation evidence, not enough
  history for predictive validation or stable threshold calibration.
- Provider security form does not prove issuer operating structure or
  domicile. Both public Universes remain explicitly provisional.
- SEC B2 published no completed source cache or issuer-structure evidence and
  remains paused.
- No point-in-time sector/industry taxonomy, market-cap dataset, fundamentals,
  valuation model, options chain, implied volatility, Greeks, open interest,
  true fund-flow data, automated daily ingestion, scheduler, database/catalog
  service, or general production API exists.
- The 2026-08-28 official Massive terms review found a material product/source
  conflict: individual-use data is described as owner-only, while the active
  equal-capability guest path serves the same provider-derived payload to other
  users. Session protection and non-commercial friend use do not establish
  permission. Owner-only non-display/derivative calculation and retention also
  require clarification. Product posture is now resolved in favor of equal-
  capability Sessions; compatible source permission remains unresolved. No
  access or deployment change has been authorized.
- Historical analytics replay current-as-of membership and are not a
  survivorship-free backtest.
- The OCI bundle helper's `--snapshot-release` shortcut still resolves the
  legacy local snapshot directory; current V2 snapshots require the supported
  explicit `--snapshot-path` plus `--bundle-release` form until this is fixed.
- The frontend production build still reports a JavaScript chunk above 500 KB,
  and active Production still serves the 20.4 MB monolithic Candidate JSON.
  Repository source has completed summary/detail payload separation but has not
  deployed it; workspace code splitting remains required before substantially
  expanding the UI.
- Repository source defines six independent Candidate strategy channels, but
  only as a typed shadow taxonomy. It has no formula, real assessment,
  historical validation, consumer, or Production integration. Fundamental
  value reversal remains explicitly unavailable without governed fundamental
  and valuation inputs; defensive rotation still needs point-in-time security
  taxonomy and channel-specific evaluation.
- ADR 0050 now defines the anti-look-ahead evaluation contracts, but no signal
  or outcome dataset exists. Current history is 29 sessions versus the fixed
  252-session research minimum; daily point-in-time Universe membership and
  completed corporate-action governance are also missing. Current-constituent
  replay is explicitly ineligible for performance claims.
- The 2026-08-27 historical-readiness audit formally returns
  `NOT_READY_FOR_PERFORMANCE_EVALUATION`: 29 EOD sessions and same-date Identity
  binding are mechanically sound, and SPY covers 29/29 sessions, but daily
  Universe membership, corporate actions, adjustment reconciliation, and
  terminal/delisting identity are absent. Every one of 286,652 retained bars
  carries `adjustment_factors_unverified` and all adjustment factors are one.
- ADR 0051 defines the source-neutral historical foundation and retention
  boundary. Repository source now implements immutable provider-neutral typed
  rows for corporate-action observations, lifecycle evidence, three-state
  daily membership, adjustment entries, and bounded coverage/readiness.
  Explicit PyArrow schemas and immutable temporary-root Parquet repositories
  now pass synthetic round-trip, hash, conflict, corruption, and path-safety
  tests. Real rows and 252/504-session history remain physically absent.
- Stock forward returns must not be described as option returns.
- Unknown, ambiguous, malformed, heuristic-only, or insufficient-evidence
  classifications remain quarantined.

## Next candidate work

The first Candidate performance slice is implemented without changing results:
physical per-stage runtime evidence, a worktree-safe Dell Python runner,
overlapping-panel shared reads, one stable-ID state bar index per panel, and
reuse of the already verified current risk ranking. On the same complete
2026-08-26 audit, time before the audit writer fell from 1840.44 to 461.88
seconds while the logical fingerprint remained
`34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
with zero Oracle mismatch. Verified-prior Candidate append is now implemented
and matches a corrected stable-prefix cold reference across every business
artifact. Real validation exposed a legacy Phase 1b rolling-window defect that
reinitialized historical state when the 26-session window advanced. State
calculation V1.0.1 now preserves a stable canonical left boundary while each
Composite retains its trailing 26-session source window. Legacy V1.0.0 audits
remain readable and Production remains unchanged.

On corrected 2026-08-26 development inputs, Candidate incremental time before
writing was 309.02 seconds versus 461.67 seconds cold. Repository source now
implements ADR 0025's optional immutable panel-stage reuse between Phase 1a
and Candidate. The final real-data comparison reduced current-panel load from
217.409 to 8.837 seconds and total time before writing from 310.008 to 101.792
seconds. Source, raw-fact, normalization, score, state, transition, risk,
parameter, and Oracle files were byte-identical; both Oracles had zero
mismatch. The cache is explicit, content-addressed, Dell-local, and fails
closed on a present invalid entry; it neither writes `/data` nor changes
Production.
Verified-prior Phase 1b append is now implemented. The final-version real
2026-08-26 incremental audit matched the V1.0.1 cold state history,
explanations, transitions, and current summary exactly with zero Oracle
mismatch; time before writing was 0.237 seconds versus 302.736 seconds cold.
Repository source now also implements ADR 0026's streaming and resumable
Candidate artifact boundary without changing completed audit schemas or
business bytes. The final real 2026-08-26 development run recorded 111.636
seconds before writing, 17.921 seconds for ten streamed artifacts, a 3,343,112
KiB process peak, and an approximately 164-second work-directory-to-delivery
boundary. Its nine source/business/Oracle files were byte-identical to the
earlier panel-cache audit, all four equivalence gates were true, and Oracle
mismatch was zero. Repository source now enforces daily verified-prior,
periodic cold-reference,
and code/model-change cold-full-replay modes under ADR 0027. A real 2026-08-26
periodic cold reference completed in 597.70 seconds; formal comparison with the
final incremental audit took 197.20 seconds and matched all eight comparable
business projections. Both audits had zero Oracle mismatch. Deterministic
process parallelism is now implemented only across independent cold-replay
session Oracles under ADR 0028. Four workers reduced the real cold Oracle stage
from 117.09 to 76.23 seconds and end-to-end time from 597.70 to 560.02 seconds;
all nine business/Oracle files were byte-identical. Daily remains one effective
Oracle worker because 2- and 4-worker inner-session prototypes were slower than
serial. ADR 0029 now adds an exact-session read-only daily state planner. A real
2026-08-26 rehearsal formally reread the corrected Phase 1b/Candidate
incremental development chain and returned `calculate_entry_geometry` as the
sole next action. It made zero external requests and Production writes and did
not enable a scheduler. ADR 0030 now adds the repository-tested single-action
offline executor and durable Dell run custody: exact plan/action binding, one
global lock, immutable hash-chained events, evidence validation, post-action
formal re-plan, and inspection-only crash recovery. It is limited to Phase 1a,
verified-prior Phase 1b, daily Candidate, and entry geometry. No durable real
analytics action has yet been executed through it; the run root was later
provisioned for the controlled acquisition/Apply rehearsal recorded below.
Session-readiness/retry policy and provider acquisition/canonical-apply
standing authorization were the next boundary. ADR 0031 now adds the
repository-tested, network-free readiness decision: actual XNYS close and
early-close handling, 30-minute provisional stabilization, bounded
retry/`Retry-After`, five-attempt
and six-hour limits, explicit alert state, and oldest-missing-session recovery.
It makes no provider-completeness claim and performs no fetch, apply,
notification, or scheduler action. Durable acquisition-attempt custody and
the standing-authorization decision were next. ADR 0032 now adds repository-
tested reservation/outcome/recovery custody under the shared global lock and
cross-session journal. It binds a fresh exact readiness fingerprint, package
path/type/session/request count/hashes/timing, persists bounded retry evidence,
and never loads credentials or executes a request. No real journal root or
fetch attempt was created. Provider fetch/canonical-apply standing
authorization is now repository-defined by ADR 0033 with a maximum 90-day
window, exact host/provider/path/code/readiness bindings, an external whole-
file SHA pin, and a four-operation Identity/EOD scope. No real authorization
directory, artifact, pin, or transition exists; current real operations still
require manual approval. ADR 0034 now adds the repository-tested coordinator
core with one-transition maximum, default-absent provider/apply capabilities,
explicit recovery stops, opt-in offline execution, and a hard stop at
publication review. That slice introduced no CLI, installed adapter,
authorization activation, request, or write.
ADR 0035 now adds repository-tested canonical Identity/EOD Apply custody under
journal 1.2. Reservation binds the completed acquisition, frozen plan SHA,
package hashes, expected inventory, absent targets, and exact paths; recovery
never writes and distinguishes formally complete, provably untouched, and
partial/ambiguous state. No real Apply reservation, recovery, or `/data` write
occurred through this layer.
ADR 0036 now adds repository-tested standing-authorized fetch/Apply capability
adapters. They preflight the external grant before reservation or credential
access, bind acquisition/Apply starts to request 1.1, preserve actual bounded
Identity HTTP request counts, and leave unknown fetch or any Apply exception
unresolved for recovery. The corrected authorized canonical root is
`/data/trading-intelligence-platform`; coordinator contract was then 1.1. The
ports remain absent unless explicitly installed, and that slice created no real
authorization, host pin, credential read, request, Apply, CLI, or scheduler
entry.
ADR 0037 now adds a default-disabled one-transition CLI and externally
SHA-pinned host-runtime contract. Capability installation requires an explicit
flag, enabled owner-only config, and independently derived actual Dell hostname,
executing source root, clean HEAD, and readiness-policy fingerprint. No real
host config, CLI invocation, service, timer, alert, or scheduler exists. The
CLI now has ADR 0038's explicit, mutually exclusive recovery mode. It rereads
one exact pending acquisition, Apply, or offline event and invokes only the
matching existing no-request/no-Apply/no-replay recovery boundary. Coordinator
contract is 1.2. This route is repository-tested only; no real recovery or
run-journal transition occurred.
ADR 0039 advances the coordinator to 1.3, preserves alert-required state, and
adds an explicitly emitted deterministic alert intent for blocked, interrupted,
or missed-session attention states. It never claims delivery: no channel,
outbox, credential, retry, receipt, or real notification is implemented.
External runtime/authorization provisioning remains deferred while exact-
revision-bound control code is still changing.
ADR 0040 adds a separate owner-only, immutable alert-delivery journal and one-
attempt custody port. It reserves before transport, requires bounded terminal
evidence, returns an already-delivered intent without another call, and blocks
known-failed or unresolved retries. ADR 0041 adds the first concrete channel:
a default-disabled SMTP adapter with exact-revision external config, separate
owner-only credentials, verified TLS, deterministic bilingual content, and
conservative unknown-outcome handling. It is repository-tested only: no email
config, credential, alert root, transport call, or delivery exists. ADR 0042
adds a read-only joint config preflight that verifies all three external
artifacts at one clean Dell revision while prohibiting credential access,
networking, writes, and activation. The command is repository-tested only; no
real external artifacts were provisioned or preflighted. ADR 0043 adds the
explicit post-coordination CLI composition from a non-null intent through
alert custody to SMTP. Default and normal-state paths remain zero-delivery;
only synthetic credentials and a fake sender have exercised this route. ADR
0044 advances joint preflight to 1.1 with an explicit no-email data-only mode;
the full four-operation data scope remains mandatory and email inputs must be
clearly included or omitted.
Publication, Snapshot generation, bundle construction, and OCI deployment
remain separate explicit approvals.

The 2026-08-27 20:18Z read-only Dell check found latest canonical Identity/EOD
at 2026-08-26 and selected `prepare_identity_catchup` for 2026-08-27. Readiness
was still in the post-close stabilization window until 20:30Z. A second
network-free check at exactly 20:30Z advanced only to
`ready_for_fetch_review` / `review_fetch_authorization`, with zero attempts,
requests, and writes. No daily run root, alert root, matching user timer,
external Host Runtime, or standing authorization was installed; no credential,
provider fetch, or write was performed.

That review was later explicitly authorized. At exact revision `c3af030`, the
installed seven-day data-only external controls passed preflight. Same-day
Identity fetched in 14 requests and canonical Identity 2026-08-27 formally
completed: 13,148 provider-identity rows and 9,982 instrument/resolver rows.
The next EOD fetch made one request but terminated `permanent_failure`; no EOD
package, staging residue, approval plan, or canonical 2026-08-27 EOD target
exists. The old terminal does not retain the numeric HTTP status, so the exact
cause is unverified and no retry occurred. Canonical EOD therefore remains
2026-08-26, while Identity is now 2026-08-27.

ADR 0045 adds bounded request-count and numeric HTTP-status evidence for future
failures without retaining response content or changing failure classification.
The repository change invalidates the installed `c3af030` exact-revision
controls until separately reviewed and reprovisioned. Publication, deployment,
email, and scheduler authority remain absent.

ADR 0046 advances the credential-free context report to 1.1. It no longer
labels latest-EOD provenance as the overall Identity state; it separately
reports latest Identity, latest EOD's bound Identity, and their alignment.

ADR 0047 advances readiness to 1.1, acquisition custody to 1.2, the coordinator
to 1.4, and the backward-compatible run journal to 1.3. The active Basic EOD
profile now requires an immutable, bounded operator availability review before
a first current-session EOD request. A permanent/quality terminal can be
released for exactly one later bounded fetch review only by an event tied to
its exact terminal fingerprint. The review CLI is offline and grants no fetch,
Apply, scheduler, publication, or deployment authority. It has now appended
one real review tied to the exact 2026-08-27 terminal. Readiness remains
`waiting_to_retry` until 2026-08-28T16:00:00Z and no retry is authorized by
the review itself; the legacy HTTP status remains unknown.

The information-hierarchy and current-payload change layer are implemented in
repository source: first-level workspaces, shared controls, an opaque sticky
header, factual first-screen summaries, one-/five-session Regime deltas, both
threshold distances, relationship prior-state persistence, decision-lane
highlights, and the Universe/comparable explanation. Exact first-seen dates,
multi-session relationship persistence counts, and evidence acceleration need
an additive reviewed analytics-response contract; they are not inferred in the
browser.

The Phase 5 stock-candidate pipeline and Phase 6 consumer integration are
active: strict fact/component/confidence/batch contracts, a fingerprinted
seven-component parameter set, pure 26-session scoring, missingness and anomaly
quarantine, separate Conservative/Balanced/Aggressive eligibility/ranking,
chronological Watch/Prepare/Enter/invalidated replay, independent Oracles,
canonical `/tmp` audit/reread boundaries, Candidate publication 1.1, MI 1.2,
Snapshot 1.7 / Dashboard 2.4, and strict frontend parsing. Earlier contracts
remain readable rollback boundaries.

Candidate Entry Geometry V1 remains separate from leadership score/state/rank.
It uses fixed SMA/ATR/return/gap/range/volume facts to distinguish bounded
breakout, breakout watch, orderly pullback, strong-but-extended, and no viable
setup. The active UI selects fixed review-now, watch-trigger, wait-reset, and
other-research lanes from the complete hard-risk-qualified population; it does
not convert stock-price structure into an option-return claim.

The formal 2026-08-26 Candidate audit is
`/tmp/whalpha-candidate-phase5c-20260826`, fingerprint
`34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`;
the bound entry audit is `/tmp/whalpha-candidate-entry-20260826`, fingerprint
`b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46`.
Both formal rereads passed with zero Oracle mismatch and zero network or
Production writes; entry input-permutation equivalence is true. Primary has
53 technical-review-ready, 1,250 monitor-for-trigger, 109 wait-for-reset, and
303 deprioritized records. It has 98 strong-but-extended setups, so strength
does not automatically become an entry instruction.

ADR 0049 now defines a repository-only six-channel Candidate shadow contract:
momentum breakout, strong-stock pullback, trend continuation, technical
reversal, fundamental value reversal, and defensive rotation. It requires one
explicit result per security/channel, within-channel ranking only, visible
market fit, source-dated evidence, first rejection, counterevidence,
reviewability conditions, and invalidation. Event evidence is auxiliary;
price-derived relationships remain proxies; stock results remain distinct
from option returns. No formula, threshold, real-data assessment, Market
Intelligence/Snapshot field, UI, publication, or deployment was added.

The next evaluation boundary is also repository-defined: one sealed signal
record contains only contemporaneously available source sessions and exact
point-in-time membership, while 1/3/5-session stock outcomes mature in separate
records later. The fixed policy prohibits random splits, uses chronological
50/25/25 development/validation/holdout boundaries, purges/embargoes the
overlapping five-session label window, quarantines corporate-action ambiguity,
and never labels a stock outcome as option performance. This is a typed
contract only; no real signal/outcome row or performance statistic exists.

The read-only historical-readiness audit confirms that the short retained
panel cannot close those gaps. It contains 10,048 unique bar instruments and
9,672 present in every session, but adjacent sessions add 520 and lose 411
rows without governed lifecycle causes. The first/latest Identity snapshots
contain only `active` records; 84 first-snapshot IDs disappear and 187 latest-
snapshot IDs are new, with zero inactive/delisted rows or terminal trade dates.
With a 26-session feature window, the panel can mature at most 3 one-session,
1 three-session, and 0 five-session signal dates. Use it only for mechanics.

ADR 0051, Historical Research Data Foundation V1, and its repository-evidenced
source capability matrix are now accepted. They require separate raw EOD,
point-in-time Identity, daily membership, corporate-action, lifecycle, and
adjustment families; preserve effective/source-available/ingested clocks; and
set 252 sessions as the acquisition floor with 504 preferred.

The 2026-08-28 public-source review and Dell storage/request plan are now
complete. Basic publicly advertises five calls/minute, two years of EOD,
reference, and corporate-action history with the required Grouped Daily, All
Tickers, Splits, and Dividends shapes. A 504-session EOD+Identity projection is
about 1.66 GB before new families, so disk is not the blocker; historical
Identity pagination would take roughly 28–40 serial hours from the current
29-session base. Provider permission, live endpoint entitlement, and missing
merger/successor/terminal sources block a real pilot. Repository-safe work now
includes saved synthetic Massive split/dividend mapping, independent Decimal
adjustment invariants, and `historical-research-pilot-plan/1.0`. The planner
accepts only caller-supplied fingerprinted inventory, subtracts existing exact
sessions, enforces the 80-request/zero-retry/15-second-serial boundary, and
derives deterministic future `/tmp` package paths. It performs no storage scan,
request, credential access, or write and permanently returns `not_authorized`.
ADR 0052 and Data Record Governance V1 now add one executable cross-family
registry and orthogonal disposition, evidence, quality, coverage, point-in-time,
retention, content-scope, and serving dimensions. They do not rewrite existing
records. ADR 0053 now adds a default-deny approval review and deterministic
preceding-window selector. The preliminary dates are 2026-07-14 through
2026-07-16 with a 75-request ceiling and no unnamed Ticker Events. It emits no
acknowledgement while source permission, entitlement, lifecycle coverage, and
a fresh exact inventory fingerprint remain unresolved. The next transition is
external evidence review, not acquisition.

The active Candidate JSON is about 20.4 MB. Repository source now implements
Snapshot 1.8 / Dashboard 2.5 summary/on-demand-detail delivery without changing
Candidate publication 1.1: the real 8/26 first-load file is 1.49 MB (92.68%
smaller), with 32 detail shards and exact full-publication reconstruction.
This development candidate is not published or deployed; active Production
remains Snapshot 1.7 / Dashboard 2.4. Dell remains
the sole heavy-compute, historical-storage, and data-governance authority;
OCI is only the static serving/Session boundary. The optimized full and
incremental Candidate calculations retain serial state/order custody. Cold
replay alone may use the bounded session-Oracle process pool; daily append uses
one effective Oracle worker. Provider requests retain their fixed serial
request gates.

## Verification entry point

Run the local, credential-free report from the repository root:

```bash
scripts/admin/report-current-context.sh
```

The report is read-only, performs no network request, and validates the local
repository, `/data`, active EOD/Identity/Activation/Market Intelligence/
Snapshot state, inventory, and publication residue. Use
`--full-source-validation` when a slower complete Market Intelligence source
reread is required.

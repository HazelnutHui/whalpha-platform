# Dashboard Snapshot V2 Operations

## Market Intelligence consumer binding

The active release is Snapshot 1.11 / Dashboard 2.8. Repository source also
supports older readable pairs, including Snapshot 1.8 / Dashboard 2.5 for
split Candidate delivery. Its
dry-run receives an explicit `--market-intelligence-publication-id`, formally
reads the active immutable publication, and freezes that reference in candidate
and plan. It never discovers a latest analytics directory. Analytics and
Snapshot publication remain separately approved operations. Snapshot 1.6
requires MI 1.1 and adds the exact bound `opportunity-candidates.json`; it
cannot be produced from an MI 1.0 publication.

Snapshot 1.7 requires MI 1.2 and Candidate publication 1.1. It keeps the same
file name but upgrades the envelope to `opportunity-candidate-snapshot/1.1`
and freezes entry-audit, entry-parameter, and lane-consumer fingerprints. A
mixed or incomplete version pair fails closed.

Snapshot 1.8 keeps MI 1.2 and Candidate publication 1.1 unchanged. It emits a
compact summary plus deterministic stable-ID detail shards. The reader validates
every file, reconstructs the original full Candidate publication, and fails
closed on any missing shard or summary/detail drift. Approval plan 2.3 freezes
the ordered shard list and summary identity. Snapshot 1.8 remains a readable
compatibility boundary; active Production uses the additive 1.11/2.8 pair.

Repository source now also supports Snapshot 1.9 / Dashboard 2.6 through
Approval Plan 2.4. It extends every 1.8 binding and additionally freezes the
strategy filename, product contract/fingerprint, audit-manifest hash, audit
fingerprint, and parameter fingerprint. Plan creation, approved apply, and
verify-then-link all revalidate those fields. A 1.9 dry-run receives the exact
strategy audit through `--candidate-strategy-audit`; that input must be a
regular directory under `/tmp`, and the resulting Plan 2.4 freezes its content
identity before Apply. The historical 2026-08-28 analysis release passed Plan 2.4,
Apply, formal reread, bundle validation, and OCI guest postflight.

The Dell-local publication/bundle evidence and its explicit Production
boundary are recorded in
[Candidate Strategy Publication / Bundle Review](../audits/candidate-strategy-publication-bundle-review-2026-08-28.md).

Repository source additionally supports Snapshot 1.10 / Dashboard 2.7 through
Approval Plan 2.5. A dry-run must provide both the existing same-session
Strategy audit and the exact Visual Context audit using
`--candidate-visual-context-audit`. The builder formally rereads that `/tmp`
audit once and embeds its records into detail-shard 1.1; the summary remains
unchanged. Plan 2.5 freezes the visual audit manifest hash, logical fingerprint,
batch fingerprints, and all shard hashes. Direct publication, OCI bundle
validation, and the active Production release remain backward-compatible with
this pair; no unattended write-capable daily control plane is installed.

Repository source now also supports Snapshot 1.11 / Dashboard 2.8 through
Approval Plan 2.6. It requires MI 1.3 and therefore the exact Sector ETF
Rotation audit/product binding, while retaining every Snapshot 1.10 Strategy
and Visual Context requirement. The builder writes one dedicated checksum-
bound `sector-etf-rotation.json`; strict reread and Apply validation reject
lineage, record-order, window, Oracle, Theme-unavailable, or proxy-disclosure
drift. The browser retrieves this file only when the Sector Rotation workspace
opens. The active 2026-09-03 Snapshot and OCI release use this exact pair.

## Daily control-plane custody

ADR 0070 adds only Snapshot Approval Plan preparation to the Dell daily
executor. The read-only planner advances to
`prepare_dashboard_snapshot_plan` only when the exact Market Intelligence
publication named by the formal daily MI plan is active. The one action binds
an explicit UTC generation time, new direct-child `/tmp` output and plan paths,
the exact active MI payload/logical fingerprints, the target session, and the
same-session Strategy Channel audit.

The current planner recognizes Plan 2.6 and formally rereads it through strict
canonical, owner-controlled, regular-file, non-symlink, mode `0444` custody
and the full existing candidate/plan validation. Automation Plan 1.8 and
Executor 1.5 now generate and pass the exact Candidate Visual Context audit.
Persistent-workspace compatibility for the older audit CLIs remains a separate
activation blocker. Successful preparation stops at
`review_snapshot_publication`. It creates no `/data` target or active pointer
and conveys no Apply, bundle, deployment, rollback, or scheduler authority.
ADR 0071 adds the separate default-off daily write-custody boundary. It is
reachable only through an explicit, host-pinned one-shot invocation carrying
the exact Plan 2.6 whole-file SHA and current Snapshot state fingerprint plus
any exact stale-review acknowledgement. Default planning still stops here.

The one-shot port reserves `dashboard_snapshot_apply_started` before invoking
the existing publisher and records success only after the exact active release,
contracts, aggregate, manifest, session, target, and planned pointer formally
reread. Recovery never applies or links: exact active state reconciles success;
absent target/staging with unchanged Snapshot and Activation state proves no
write; everything partial, changed, or ambiguous blocks. The custody boundary
reserved and formally recorded the active 2026-09-03 Snapshot Apply.

## Safety boundary

The publisher and rollback tools are offline administrator workflows. They do
not fetch EOD or provider data. Never run apply while canonical freshness is
stale unless one of the versioned exact review contracts matches every bound
field and acknowledgement.

```bash
scripts/admin/publish-dashboard-snapshot-v2.sh --help
scripts/admin/rollback-dashboard-snapshot-v2.sh --help
```

Default publication creates only a review candidate under `/tmp`. An approval package additionally requires an explicit persistent `/tmp` output root. Production apply requires all of `--apply`, `--approved-plan`, `--approved-plan-sha256`, and `--expected-current-state-fingerprint`. Bare apply and partial approval arguments return exit code 2.

Approval-plan construction formally reads the active Snapshot once and binds
both its rollback reference and expected current-state fingerprint to that
single observation. Apply and verify-then-link do not reuse that object: they
perform a fresh current-state comparison, so a change after planning still
fails closed.

`--verify-then-link` uses the same approvals and only recovers a completed immutable target left inactive after a confirmed crash boundary. Rollback is independently authorized: dry-run reports the active pointer fingerprint and exact prior release; apply requires that fingerprint through `--expected-active-pointer-fingerprint` and rechecks it under lock.

## Recovery matrix

| Observable state | Meaning | Safe action |
| --- | --- | --- |
| target absent, pointer old/absent | no completed publish | create a new reviewed plan after freshness is restored |
| target completed, pointer old/absent | target rename completed; link did not | formally validate, then separately authorize verify-then-link with the original plan |
| target completed, pointer new | publication active | formal reread; do not replay apply |
| staging only | incomplete operation | fail closed and diagnose; do not treat it as completed |
| malformed/dangling pointer | ambiguous or corrupt active state | fail closed; no compatibility fallback |

OCI packaging must name an explicitly approved immutable release and never discover the newest directory automatically.

For the one approved stale review, the Snapshot CLI additionally requires an
explicit analysis session and the exact versioned review fields used by the
active Market Intelligence release. Apply or verify-then-link accepts only the
canonical plan plus full-file SHA, current-state fingerprint, exact analysis
session, and acknowledgement. The formal XNYS state is checked before and
inside the lock; any session/lag/expected-date drift fails closed. Ordinary
stale snapshots remain ineligible.

ADR 0059 adds the separately approved
`production-review-deployment/1.1` binding for actual/analysis 2026-08-26,
expected 2026-08-27, lag one, and the exact acknowledgement
`I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1`. Version 1.0 remains readable and
cannot be mixed with this binding. There is still no generic stale switch.

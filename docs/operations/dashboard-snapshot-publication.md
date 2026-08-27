# Dashboard Snapshot V2 Operations

## Market Intelligence consumer binding

The active release is Snapshot 1.7 / Dashboard 2.4. Repository source also
supports Snapshot 1.8 / Dashboard 2.5 for split Candidate delivery. Its
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
the ordered shard list and summary identity. This support is development-only;
the active Production release remains 1.7/2.4.

## Safety boundary

The publisher and rollback tools are offline administrator workflows. They do not fetch EOD or provider data. Never run apply while canonical freshness is stale.

```bash
scripts/admin/publish-dashboard-snapshot-v2.sh --help
scripts/admin/rollback-dashboard-snapshot-v2.sh --help
```

Default publication creates only a review candidate under `/tmp`. An approval package additionally requires an explicit persistent `/tmp` output root. Production apply requires all of `--apply`, `--approved-plan`, `--approved-plan-sha256`, and `--expected-current-state-fingerprint`. Bare apply and partial approval arguments return exit code 2.

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

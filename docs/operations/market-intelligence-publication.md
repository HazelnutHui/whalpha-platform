# Market Intelligence Publication Runbook

## Safety boundary

`scripts/admin/publish-market-intelligence.sh` is offline and has no implicit
mode. Planning writes only a new explicit `/tmp` directory. Apply,
verify-then-link, and rollback are separately explicit and lock-protected.

## Plan and dry-run

Planning requires exact data root, analysis session, revision, preview bundle,
Phase 1a/1b/2 audits, output/plan paths, UTC timestamp, and expected Production
inventory fingerprint. It formally rereads EOD, same-day Identity, Activation,
and source custody before emitting two candidate files and one canonical plan.

The plan freezes source hashes, current inventory and consumer state, target
absence, artifact paths/hashes/sizes, aggregate hash, publication/pointer
identity, freshness, inventory delta, recovery, and rollback. The future
`--approved-plan-sha256` is the full-file SHA, not the internal content digest.

Freshness uses actual UTC and the formal XNYS calendar. A stale historical
candidate may be reviewed, but its plan records `activation_allowed=false`;
apply and verify-then-link reject it before creating Production paths. A fresh
plan must be regenerated after catch-up.

The sole exception is the exact `production-review-deployment/1.0` contract.
Planning must explicitly pass `--review-deployment`, the approved as-of
session, expected session, lag, and acknowledgement. Apply/verify-then-link
must pass the identical acknowledgement in addition to the canonical plan,
full-file plan SHA, session/revision, and current-state fingerprint. The lock
recomputes formal freshness and requires actual `2026-08-24`, expected
`2026-08-25`, `stale`, and lag one. There is no generic stale flag.

## Apply, recovery, and rollback

Apply requires `--apply`, exact data root/session/revision, absolute approved
plan, full-file SHA, and expected current-state fingerprint. Missing/bare apply
returns exit 2. Inside the lock it revalidates plan, inventory, pointer CAS,
freshness, EOD/Identity/Activation, parameters, source audits, artifact custody,
target absence, and path/symlink containment.

Files and new directories are fsynced; staging is formally reread, atomically
renamed, reread again, then the pointer is atomically written and fsynced.
Failure before target rename is zero-write. A completed target left before
pointer CAS survives inactive and only the exact plan may `--verify-then-link`.
Partial/extra/corrupt targets and replay fail closed; recovery is never automatic.

Rollback defaults to dry-run and requires the manually approved active pointer
fingerprint. It may select only the formally readable prior pointer reference;
completed releases are never changed. The first publication has no prior
in-dataset release and therefore fails closed on rollback.

## Downstream order

After a separately authorized fresh publication: build Snapshot 1.5 / Dashboard
2.2 with the explicit publication ID; separately approve/apply Snapshot; then
build OCI with both the explicit Snapshot and
`--market-intelligence-publication`. OCI deployment remains another authorization.

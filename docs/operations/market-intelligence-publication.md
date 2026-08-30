# Market Intelligence Publication Runbook

## Safety boundary

`scripts/admin/publish-market-intelligence.sh` is offline and has no implicit
mode. Planning writes only a new explicit `/tmp` directory. Apply,
verify-then-link, and rollback are separately explicit and lock-protected.

## Plan and dry-run

Planning requires exact data root, analysis session, revision, preview bundle,
Phase 1a/1b/2 audits, the completed Candidate audit, optional bound entry-
geometry audit, output/plan paths, UTC timestamp, and expected Production
inventory fingerprint. It formally rereads EOD, same-day Identity, Activation,
and source custody before emitting two candidate files and one canonical plan.
Under ADR 0060, Candidate research semantics are fully validated when the
immutable audit is finalized. MI publication then streams every declared
artifact SHA/size, validates the completion manifest, parameters, Oracle and
equivalence gates, and parses only the bounded current-session product inputs.
Plan creation requires the exact in-process evidence returned by that build.
Candidate publication 1.0 produces MI/plan 1.1; the additive entry consumer
requires `--entry-geometry-audit` and produces MI/plan 1.2. The current
repository planning path additionally requires `--sector-rotation-audit`,
strictly rereads its complete typed custody and zero-mismatch Oracle, and
produces MI/plan 1.3. It binds the exact Phase 1a audit, history source,
calculation parameters, 11-record product, and Theme-unavailable state.

ADR 0066 makes schema 1.1 daily Candidate evidence explicit and mode-aware.
Candidate construction and MI Plan/Apply rechecks use one shared projection of
the formally bound verified-prior lineage, all-true incremental/reuse gates,
and current-session independent Oracle. The Candidate payload warns that no
same-run cold replay occurred. Missing lineage or false gates fail closed;
periodic and change-triggered cold validation remain mandatory.

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

ADR 0059 adds a second exact `production-review-deployment/1.1` exception for
actual/analysis `2026-08-26`, expected `2026-08-27`, lag one, and
`I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1`. The two versions remain
independent; apply uses the acknowledgement embedded in the approved plan and
rejects any cross-version or freshness drift.

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

The active Production path remains MI 1.2 with Snapshot 1.10 / Dashboard 2.7.
Repository source implements the required Snapshot 1.11 / Dashboard 2.8
consumer, but it has not been applied or deployed. MI 1.3 may only advance
together with that complete consumer; never pair it with an older Snapshot
that would silently drop Sector Rotation. Use the explicit publication ID and exact
same-session Strategy Channel audit, separately approve/apply Snapshot, then
build OCI with both the explicit Snapshot and
`--market-intelligence-publication`. OCI deployment remains another
authorization. Older MI/Snapshot pairs remain readable rollback-compatible
boundaries.

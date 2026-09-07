# Canonical Universe Membership Publication

## Boundary

Canonical publication is Dell-local and network-prohibited. The workstation
is the compute and data authority; this operation does not deploy OCI or alter
the public Dashboard.

A Membership partition is complete only when the governed reader validates
both the two-file physical partition and its one-file publication marker. The
marker is written last. Historical Coverage and research performance remain
separate later gates.

## Daily candidate preparation

After the same-session Daily Identity Plan 1.1 source custody and canonical EOD
are complete, prepare one prospective candidate with:

```bash
scripts/admin/prepare-daily-universe-membership.sh \
  --data-root /data/trading-intelligence-platform \
  --session-date YYYY-MM-DD \
  --catalog-as-of-date YYYY-MM-DD \
  --evaluated-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --assessed-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --candidate-root DAILY_SESSION_ROOT/universe-membership-candidate
```

The daily workspace and every parent through `daily-eod/sessions` must be an
exact owner-only `0700` directory outside `/data`, `/tmp`, and the Git
repository. The command is network-prohibited, performs no canonical write,
and reports either a signal-eligible candidate, an outcome-only candidate, or
an already completed canonical publication. A partial canonical target is not
recreated; use the exact-plan recovery below.

Create the inventory-bound Apply plan only when other expected `/data` writes
for the run are complete and Apply review can follow promptly. Do not retain a
known-stale plan across MI, Snapshot, Identity, EOD, or other canonical writes.

## Before Apply

Confirm all of the following from one unchanged plan:

- plan status is `ready_for_separate_review`;
- point-in-time eligibility is `signal_eligible`;
- plan file SHA-256, plan logical fingerprint, and expected `/data` inventory
  fingerprint are recorded exactly;
- both target partitions are absent;
- no matching staging path exists;
- full focused and repository regression tests pass.

The plan's `apply_authorized=false` states that the plan is evidence, not its
own authorization. Execution requires the exact bindings as separate command
arguments.

## Ordinary Apply

Use `scripts/admin/apply-universe-membership-plan.sh` with:

- `--plan-path`;
- `--approved-plan-sha256`;
- `--expected-plan-logical-fingerprint`;
- `--expected-current-state-fingerprint`;
- `--data-root /data/trading-intelligence-platform`.

Do not use ordinary Apply when either target already exists.

## Recovery

Use the same exact bindings plus `--verify-then-complete` only after an
interrupted invocation. Recovery can:

- reuse an exact physical partition and publish the missing final marker;
- prove an exact completed pair without writing.

Recovery rejects corrupt/partial targets, marker-before-physical state,
unrelated inventory drift, staging residue, and a request with no completed
target. If nothing was published, rerun ordinary Apply after proving the
original pre-state. Inspect and resolve any other rejected state separately;
do not broaden the target or delete evidence by assumption.

## Postflight

Record:

- execution status and whether each partition was published or reused;
- published file and byte counts;
- publication fingerprint and file SHA-256;
- post-state `/data` inventory fingerprint;
- canonical formal reread row count;
- zero external requests, overwrites, and deletions.

Then run `verify_then_complete` once as a zero-write postflight. Do not call the
result Historical Coverage or strategy readiness. Daily preparation is not yet
a coordinator or scheduler action and does not gate the public website.

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

First obtain the independent read-only sidecar decision:

```bash
scripts/admin/plan-daily-universe-membership-sidecar.sh \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --as-of-session YYYY-MM-DD \
  --catalog-as-of-date YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --workspace-root /home/hui/.local/state/trading-intelligence-platform/automation/daily-eod \
  --repository-root /home/hui/projects/trading-intelligence-platform
```

This command formally rereads the current primary automation plan and existing
Membership evidence. It performs no sidecar action. `prepare_candidate` and
`prepare_apply_plan` are reviewable instructions, not authority. A `blocked`
sidecar always retains `website_pipeline_blocked=false`.

The two non-canonical workspace actions may instead be reviewed or executed as
one finite sidecar run:

```bash
scripts/admin/run-bounded-daily-universe-membership.sh \
  --as-of-session YYYY-MM-DD \
  --catalog-as-of-date YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --workspace-root /home/hui/.local/state/trading-intelligence-platform/automation/daily-eod
```

The command is review-only by default. Explicit `--execute` permits at most
candidate preparation and near-Apply plan creation under one session lock. It
does not invoke the primary pipeline, perform Membership Apply, retry, recover,
or install a scheduler. A normal successful run stops at `review_apply`.

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

The first real prospective continuation completed for 2026-09-08 on
2026-09-09. Same-session EOD, Identity, and normalized Identity source evidence
were combined with the existing completed 2026-08-14 provider type-code
catalog; an attempted nonexistent 2026-09-08 catalog binding correctly failed
before writes. The corrected candidate was signal eligible, exact Plan/Apply
published 19,964 decisions, and `verify_then_complete` reused both targets with
zero writes. This proves the manual publication path. The separate read-only
sidecar planner and bounded workspace runner are now implemented; a new-session
live observation and unattended execution remain pending. See the dated
[audit](../audits/daily-universe-membership-publication-2026-09-09.md).

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
result Historical Coverage or strategy readiness. Daily preparation is not a
coordinator or scheduler action and does not gate the public website.

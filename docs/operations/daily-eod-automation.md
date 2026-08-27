# Daily EOD Automation Control Plane

## Current scope

The daily control plane now has two deliberately separate, credential-free
parts: a read-only planner and a single-action offline executor. The planner
formally reconciles one exact target session and reports one safe next action.
The executor can consume one unchanged plan fingerprint and run only one of
the four offline analytics actions under durable Dell custody. Neither part
enables a timer.

The action order is:

```text
same-day Identity
  -> canonical EOD
  -> Phase 1a
  -> verified-prior Phase 1b
  -> daily verified-prior Candidate
  -> Candidate entry geometry
  -> publication review
```

Acquisition and canonical `/data` apply remain authorization boundaries.
Publication, Snapshot, bundle, OCI deployment, and scheduler activation are
outside both commands.

## Read-only plan

Every audit path is explicit and must be a distinct direct child of `/tmp`.
The previous Phase 1b and Candidate paths must be the immediately preceding
XNYS session. No `latest` lookup is allowed.

```bash
scripts/admin/plan-daily-eod-automation.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1a-audit /tmp/<current-phase1a> \
  --prior-phase1b-audit /tmp/<immediately-prior-phase1b> \
  --phase1b-audit /tmp/<current-phase1b> \
  --prior-candidate-audit /tmp/<immediately-prior-candidate> \
  --candidate-audit /tmp/<current-candidate> \
  --entry-geometry-audit /tmp/<current-entry-geometry>
```

The JSON result has one of four statuses:

- `waiting_for_authorized_input`: prepare the exact Identity or EOD catch-up;
- `ready_for_offline_calculation`: run only the named offline analytics step;
- `analytics_ready`: all current analytics formally reread and publication may
  be reviewed separately;
- `blocked`: stop and diagnose; do not overwrite or skip the failed boundary.

`blocked` exits 1. The other planning states exit 0 because they are valid
states, not completed actions.

## Offline entry step

The worktree-safe administrator entry is:

```bash
scripts/admin/calculate-candidate-entry-geometry-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --candidate-audit /tmp/<exact-current-candidate-audit> \
  --output-dir /tmp/<new-current-entry-geometry-audit>
```

This direct entry remains useful for diagnosis and explicitly supervised work.
For a custody-tracked daily transition, use the single-action executor below.

## Single-action offline execution

Provision one stable owner-only run root on Dell before first use. It must be
outside the repository and `/data`; the executor will not create or repair the
root. The example location is illustrative and is not created by repository
code:

```bash
install -d -m 0700 /home/hui/.local/state/trading-intelligence-platform/daily-eod
```

First run the read-only planner and review its exact
`logical_content_fingerprint` and `next_action`. Then execute that one action
with the same explicit path set:

```bash
scripts/admin/execute-daily-eod-offline-action.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1a-audit /tmp/<current-phase1a> \
  --prior-phase1b-audit /tmp/<immediately-prior-phase1b> \
  --phase1b-audit /tmp/<current-phase1b> \
  --prior-candidate-audit /tmp/<immediately-prior-candidate> \
  --candidate-audit /tmp/<current-candidate> \
  --entry-geometry-audit /tmp/<current-entry-geometry> \
  --run-root /home/hui/.local/state/trading-intelligence-platform/daily-eod \
  --panel-cache-root /tmp/<immutable-panel-cache> \
  --candidate-work-dir /tmp/<owner-controlled-candidate-recovery> \
  --execute-action <exact-next-action> \
  --expected-plan-fingerprint <64-hex-plan-fingerprint>
```

Only `calculate_phase1a`, `calculate_phase1b_incremental`,
`calculate_candidate_daily`, and `calculate_entry_geometry` are executable.
The Candidate work directory is required only for the Candidate action. The
panel cache is optional and must remain outside `/data`.

The executor acquires one global non-blocking lock, re-plans under the lock,
records an immutable start event, invokes exactly one existing offline command,
validates its evidence, formally re-plans, and records a terminal event. A
successful child exit is not success unless the planned stage formally rereads
as complete and the next action advances. Re-run the read-only planner before
requesting another action; do not reuse an old fingerprint.

The run root contains one lock and date-keyed event directories. Do not edit,
rename, chmod, copy into, or remove individual event files. Events are
monotonically numbered canonical JSON, owner-read-only, and SHA-256 chained
across sessions. Any unexpected entry, permission drift, symlink, sequence
gap, malformed event, hash mismatch, or unresolved earlier session blocks
execution.

## Interrupted-action recovery

If the process stops after `action_started` but before a terminal event, do
not rerun the action. Use the exact same session and execution paths with:

```bash
scripts/admin/execute-daily-eod-offline-action.sh \
  <the-same-session-and-path-arguments> \
  --recover-incomplete
```

Recovery never calculates or writes an analytics artifact. It formally
re-plans and appends exactly one classification:

- `recovered_succeeded`: the immutable stage completion and plan advance are
  proven;
- `recovered_not_completed`: the plan and missing stage are unchanged, so a
  later explicit execution request may retry; or
- `recovery_blocked`: state is ambiguous and requires operator diagnosis.

Path drift is rejected because recovery inputs are fingerprint-bound to the
started attempt. A terminal failure or `recovered_not_completed` does not
automatically retry.

## Dell rehearsal evidence

The 2026-08-26 read-only rehearsal used the corrected verified-prior Phase 1b
and an explicit `daily`-tier Candidate development chain. It formally reread same-day
Identity/EOD, current Phase 1a, both prior/current Phase 1b and Candidate
audits, then returned `ready_for_offline_calculation` with sole next action
`calculate_entry_geometry`. Plan fingerprint:
`5f5f5be7a0e219ca21acaa01afc889f1397ca216ef7e8daab692686ee55cf21d`.

The rehearsal made zero external requests and zero Production writes and did
not create the proposed entry target. This development chain is separate from
the already completed and deployed 2026-08-26 publication chain.

## Still required before unattended operation

1. An explicit standing-authorization contract for provider fetch and
   canonical apply, or continued manual approval for those two boundaries.
2. Session-readiness timing, bounded retry/backoff, timeout, alert, and missed-
   session recovery rules.
3. Separate authorization decisions for publication, Snapshot/bundle, OCI
   deployment, and finally scheduler activation.

The executor and journal are implemented and tested, but no durable real run
root has been provisioned and no real action has been executed through this
boundary yet.

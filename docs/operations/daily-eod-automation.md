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

## Session and provider readiness

Market close is not provider readiness. Massive documents Stocks Basic as EOD
and the Grouped Daily endpoint as available across Stocks plans, but does not
guarantee a precise stable-publication minute. Daily aggregates may also be
updated for late or corrected trades. The first fetch review therefore begins
30 minutes after the actual XNYS close as a provisional operational choice,
not as a completeness claim.

The network-free readiness command is:

```bash
scripts/admin/plan-daily-eod-readiness.sh \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --target-session YYYY-MM-DD \
  --latest-canonical-session YYYY-MM-DD \
  --acquisition-action prepare_identity_catchup
```

The action must be the acquisition action reported by the exact-session daily
planner. The target must be the oldest missing XNYS session. Use
`prepare_eod_catchup` only after the same-day Identity boundary formally
completes and the daily planner advances.

Prior separately authorized fetch outcomes may be supplied in chronological
order without secrets or response content:

```bash
--attempt '1|YYYY-MM-DDTHH:MM:SS+00:00|not_ready' \
--attempt '2|YYYY-MM-DDTHH:MM:SS+00:00|rate_limited|1800'
```

Recognized outcomes are `not_ready`, `rate_limited`, `transient_failure`,
`fetch_package_ready`, `permanent_failure`, and `quality_failure`. The policy
allows at most five attempts with 15/30/60/120-minute backoff, honors a bounded
rate-limit `Retry-After`, and moves an elapsed six-hour daily deadline into
missed-session recovery. Permanent/quality failures and exhausted attempts
require diagnosis. A ready fetch package only requests separate apply review.

The result always declares zero requests/writes, no scheduler, and no provider
completeness assertion. Exit 1 means alert/diagnosis is required; it does not
send a notification. Durable attempt custody is implemented below;
notification delivery is not.

## Provider-attempt custody

Custody uses the same pre-provisioned Dell run root, global lock, and
cross-session journal as offline execution. It does not execute a provider
request. Reserve one exact readiness decision within five minutes:

```bash
scripts/admin/custody-daily-eod-acquisition.sh \
  --target-session YYYY-MM-DD \
  --latest-canonical-session YYYY-MM-DD \
  --acquisition-action prepare_identity_catchup \
  --package /tmp/<new-exact-attempt-package> \
  --run-root /home/hui/.local/state/trading-intelligence-platform/daily-eod \
  --reserve \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --expected-readiness-fingerprint <64-hex-readiness-fingerprint>
```

Reservation writes an immutable start event but prints
`provider_request_executed_by_custody=false`. A provider fetch remains a
separately authorized invocation of the existing exact-date Identity or EOD
`--fetch-only` command. After that invocation returns, record its classified
outcome with the exact same session, latest-canonical value, action, package,
and run root:

```bash
scripts/admin/custody-daily-eod-acquisition.sh \
  <the-same-custody-identity-arguments> \
  --record-outcome fetch_package_ready
```

Other outcomes are `not_ready`, `rate_limited`, `transient_failure`,
`permanent_failure`, and `quality_failure`. Only rate limiting accepts
`--retry-after-seconds`. A package-ready outcome formally rereads the frozen
package and binds exact operation, session, path, type, request count, hashes,
and reservation-to-result timing. Non-package-ready outcomes require both the
package target and its staging path to be absent.

If the external fetch process stops before an outcome is recorded, do not
rerun it. Use:

```bash
scripts/admin/custody-daily-eod-acquisition.sh \
  <the-same-custody-identity-arguments> \
  --recover-incomplete
```

Recovery performs no network access. A formally complete package is reconciled
as ready; total absence becomes a bounded transient attempt; staging, symlink,
or invalid package custody blocks the daily state machine. Terminal attempts
feed the next readiness calculation so retry delay and maximum count persist
across processes.

Custody is not the standing-authorization contract. Until that separate
decision is accepted, every real `--fetch-only` request and every canonical
apply still requires explicit approval.

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
2. Actual alert delivery and a controlled real timing rehearsal to calibrate
   the provisional 30-minute/limited-retry policy.
3. Separate authorization decisions for publication, Snapshot/bundle, OCI
   deployment, and finally scheduler activation.

The executor and journal are implemented and tested, but no durable real run
root has been provisioned and no real action has been executed through this
boundary yet. Readiness planning is also implemented and tested without making
a provider request or enabling a scheduler. Acquisition custody is implemented
and tested without creating the real run root or executing a fetch.

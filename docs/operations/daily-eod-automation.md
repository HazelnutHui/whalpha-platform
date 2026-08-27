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

Custody is not the standing-authorization contract. The contract below is now
accepted but inactive; until a real artifact and external pin are separately
approved, every real `--fetch-only` request and canonical apply still requires
explicit approval.

## Standing daily data authorization

ADR 0033 defines the repository contract for a future standing authorization.
It can cover only exact-session Massive Identity/EOD fetch and their existing
approved canonical apply boundaries. A reviewed artifact is active only when a
separately activated host configuration supplies its exact whole-file SHA-256.
It must also match the Dell host, `/data`, run root, implementation revision,
readiness-policy fingerprint, effective interval, and one exact coordinator-
derived transition. Maximum validity is 90 days.

The artifact must be a canonical owner-only `0400` JSON file directly under a
pre-provisioned owner-only `0700` authorization directory outside Git and
`/data`. The repository exposes an in-memory candidate builder and strict
reader/verifier; it does not provision the directory, write an active artifact,
or configure the external SHA pin. No active artifact currently exists.

Fetch authorization requires an unresolved custody reservation and permits at
most one request. Apply authorization requires completed package custody,
package hashes, the frozen approval-plan SHA, and its exact expected-current-
state fingerprint, and permits at most one canonical transition. Any expiry,
stale request, revision change, scope/path/hash mismatch, or unsafe artifact
custody rejects the transition.

This grant never includes publication, Snapshot, bundle, deployment, rollback,
Universe activation, SEC, intraday/options data, orders, notifications, or the
scheduler itself. Until an authorization artifact and external host SHA pin are
explicitly reviewed and activated, provider fetch and canonical apply remain
manual approvals.

## One-transition coordinator

ADR 0034 adds the repository-only coordinator core. One invocation formally
joins the exact automation plan, shared journal, and acquisition readiness and
returns or invokes at most one transition. It distinguishes wait, acquisition
recovery, offline recovery, diagnosis, manual fetch/apply authorization,
offline calculation, and publication review. It never loops or retries.

Provider fetch and canonical apply are explicit capability ports and are absent
by default. An installed capability must bind the exact target and readiness
fingerprint, return one formal event fingerprint, and cannot claim more than
20 Identity HTTP requests, one EOD HTTP request, or one canonical Apply. The
ADR 0036 adapters independently satisfy ADR 0032, ADR 0033, and ADR 0035; the
coordinator does not grant authority.
Offline execution is also opt-in per invocation and delegates exactly one
action to ADR 0030.

There is no coordinator CLI or scheduler entry yet. The capability ports remain
uninstalled by default. No real run root, authorization artifact, credential
read, provider request, or canonical write was created by this implementation.

## Canonical Apply custody

ADR 0035 adds `daily-eod-canonical-apply-custody/1.0` and the third disjoint
`daily-eod-run-journal/1.2` event family. Before an external Identity/EOD Apply,
reservation proves the latest exact acquisition package, current apply-review
readiness, frozen plan and whole-file SHA, package hashes, expected canonical
inventory, absent targets, and exact paths under the shared global lock. It
then records `canonical_apply_started` without executing Apply.

A successful external Apply may close the attempt only after the exact-session
automation planner formally proves the named canonical stage complete and
advanced. Any exception or failed postcondition remains unresolved. Recovery
never writes: it records success when formal readers prove completion, not
completed only when every target is absent and the entire inventory is
unchanged, or blocked for partial/changed/ambiguous state. Partial Identity
publication may use the existing `verify-then-complete` boundary only after
separate diagnosis and authorization.

No Apply adapter is installed and there is no CLI for this custody layer; no
real journal root or Apply was created.

## Authorized capability adapters

ADR 0036 adds executable but explicitly uninstalled fetch and Apply adapters.
They reread and preflight the externally SHA-pinned grant before reservation,
bind the new custody start into authorized-transition request 1.1, and only
then cross the existing credential/network or canonical-write boundary.
Authorization file/content hashes are retained on the start and the decision
fingerprint on a formally completed terminal.

Identity uses a per-invocation counting transport and reports its actual 1–20
HTTP requests; EOD remains exactly one. Known bounded provider outcomes are
recorded normally. Unexpected fetch exceptions and every Apply exception stay
unresolved for explicit recovery, so neither request nor Apply is silently
replayed. The authorized canonical root is
`/data/trading-intelligence-platform`, not `/data`.

Construction performs no I/O, and the coordinator receives no capability
unless one is explicitly supplied. No real adapter was installed or invoked;
no authorization artifact, host SHA pin, credential read, request, Apply,
notification, or scheduler state exists.

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

1. A default-disabled host configuration and coordinator CLI that can install
   the ADR 0036 adapters only from explicit external authorization paths and
   SHA pin, followed by review/provisioning or continued manual approval.
2. Actual alert delivery and a controlled real timing rehearsal to calibrate
   the provisional 30-minute/limited-retry policy.
3. Separate authorization decisions for publication, Snapshot/bundle, OCI
   deployment, and finally scheduler activation.

The executor and journal are implemented and tested, but no durable real run
root has been provisioned and no real action has been executed through this
boundary yet. Readiness planning is also implemented and tested without making
a provider request or enabling a scheduler. Acquisition custody is implemented
and tested without creating the real run root or executing a fetch. Standing
authorization validation is implemented and tested, but no real authorization
directory, artifact, SHA pin, or authorized transition exists. The coordinator
core is implemented and tested with default-absent provider/apply capabilities;
it has no real CLI or scheduler entry. Canonical Apply reservation and no-write
recovery are repository-tested under journal 1.2, but no real Apply adapter,
reservation, or recovery ran. ADR 0036 adapters are repository-tested but have
not been installed or invoked against real authorization, credentials, Massive,
or `/data`.

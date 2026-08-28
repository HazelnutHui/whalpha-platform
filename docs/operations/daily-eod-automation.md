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
updated for late or corrected trades. Identity's first fetch review begins 30
minutes after the actual XNYS close as a provisional operational choice, not
as a completeness claim. Readiness 1.1 also records an explicit provider-
recency profile. Under the active `massive_stocks_basic_end_of_day` profile, a
first current-session EOD request does not become reviewable from the 30-minute
clock alone. It requires one immutable operator availability review with an
explicit `not_before` time. Older missing sessions retain oldest-first recovery
without inventing a current-session release gate. The exact Basic current-
session availability time remains unproven.

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

ADR 0045 advanced acquisition custody to 1.1. ADR 0047 advances it to 1.2 and
readiness to 1.1. Authorized fetch outcomes now retain the exact bounded
request count and, for provider redirect/client
responses, only the numeric HTTP status. Response bodies, URLs, headers,
request IDs, provider messages, and credentials remain excluded. Status
evidence does not make a permanent failure retryable.

ADR 0047 adds the offline operator-review command. It appends one immutable
journal event but never reserves, authorizes, or executes a provider request:

```bash
scripts/admin/review-daily-eod-acquisition.sh \
  --target-session YYYY-MM-DD \
  --latest-canonical-session YYYY-MM-DD \
  --acquisition-action prepare_eod_catchup \
  --run-root /home/hui/.local/state/trading-intelligence-platform/daily-eod \
  --package /tmp/<future-exact-attempt-package> \
  --purpose initial_eod_availability \
  --disposition authorize_one_fetch_after \
  --evidence-code provider_plan_and_release_reviewed \
  --not-before YYYY-MM-DDTHH:MM:SS+00:00 \
  --acknowledgement I_UNDERSTAND_REVIEW_DOES_NOT_EXECUTE_OR_AUTHORIZE_FETCH
```

For terminal recovery, use purpose `terminal_failure_retry` and bind
`--expected-terminal-event-fingerprint` to the exact latest permanent/quality
terminal. Allowed diagnosis codes are bounded by the CLI. The standard retry
schedule and five-attempt limit still apply. Package-ready history cannot be
reopened. Do not invoke this command merely to clear a blocker; first establish
the non-sensitive diagnosis and a defensible `not_before` time.

The result always declares zero requests/writes, no scheduler, and no provider
completeness assertion. Exit 1 means alert/diagnosis is required; this command
does not send a notification. Durable attempt and alert-delivery custody plus a
default-disabled SMTP library adapter are described below; no real transport
or notification command is installed.

### 2026-08-27 real terminal-review state

The 2026-08-27 EOD terminal event is bound by one immutable review recorded at
2026-08-27T22:24:36.997840Z. Its `not_before` is
2026-08-28T16:00:00Z. Before that instant, the formal offline state is
`waiting_to_retry` / `wait` with
`operator_review_not_before_pending`. The review records zero requests and
zero Production writes and explicitly reports
`fetch_authorized_by_review=false`.

The boundary uses the following public evidence:

- Massive documents the Grouped Daily endpoint as included across Stocks
  plans and Stocks Basic as end-of-day, but publishes no exact stable REST
  release minute:
  <https://massive.com/docs/rest/stocks/aggregates/daily-market-summary>
- The Stocks plan page describes Basic as end-of-day:
  <https://massive.com/pricing?product=stocks>
- Separate Stocks flat-file documentation says finalized daily flat files are
  generally available around 11:00 ET on the following day:
  <https://massive.com/docs/flat-files/stocks/overview?assetClass=stocks&license=personal&name=stocks_basic>

The selected 12:00 ET next-day boundary adds one hour to that approximate
flat-file time. This is a stability-first operator inference, not a statement
that the Basic plan includes flat files, not a REST service-level guarantee,
and not proof that the 2026-08-27 REST dataset is complete. At or after the
boundary, first rerun the offline readiness check. A real request still needs
a separate exact fetch-authorization review and valid exact-revision external
controls.

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

At the ADR 0034 slice there was no coordinator CLI or scheduler entry. ADR 0037
subsequently added the default-disabled CLI, and ADR 0038 added explicit
one-event recovery routing. Capability ports remain uninstalled by default.
No real run root, authorization artifact, credential read, provider request,
or canonical write was created by the coordinator implementation.

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

No Apply adapter is installed and there is no standalone Apply/recovery CLI for
this custody layer; no real journal root or Apply was created.

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

## Host-gated one-transition CLI

ADR 0037 adds `daily-eod-host-runtime-config/1.0` and
`scripts/admin/run-one-daily-eod-transition.sh`. The CLI takes only explicit
session and artifact paths and calls the coordinator once. Authorized ports are
absent by default, and a socket guard remains active in that mode.

Installing the ports requires `--enable-authorized-capabilities`, an absolute
external host-config path, and its exact external whole-file SHA. The canonical
owner-only config must also enable capabilities and match the actual Dell
hostname, executing repository source, completely clean Git HEAD, current
readiness policy, data/run roots, authorization SHA, and credential path. The
credential is not read during host-runtime verification. Approved-plan and
expected-state fingerprints must be provided together before Apply.

The CLI may opt into one existing offline calculation with `--execute-offline`,
but never loops and never gains publication, deployment, or scheduler
authority. ADR 0038 adds mutually exclusive `--recover-unresolved`: it
formally rereads the one exact pending event and invokes only its acquisition,
canonical-Apply, or offline-action recovery boundary. The socket guard remains
active; recovery never requests provider data, performs Apply, replays a
calculation, retries, or loops. Exceptions without formal
terminal evidence report request/write counts as unknown, never as assumed
zero. No real host/runtime config,
CLI invocation, service, timer, or scheduler was created.

## Alert intent boundary

ADR 0039 adds `daily-eod-alert-intent/1.0` and coordinator 1.3. Blocked states,
an unresolved interrupted transition, and missed-session attention now retain
`alert_required=true` in the coordinator fingerprint. To expose the
channel-neutral envelope, add:

```bash
--emit-alert-intent
```

The JSON result then contains `alert_intent`. Repeated observation of the same
target and exact coordinator state produces the same deduplication key. A
normal state returns `alert_intent: null`.

This is not delivery. The intent always records `delivery_attempted=false`,
zero external requests, and zero Production writes. ADR 0040 supplies the
separate uninstalled custody boundary below, but no real outbox/root, channel,
credential, retry, escalation, or delivery receipt exists. Do not configure a
timer on the assumption that printing the intent notified anyone. Exceptions
before a formal coordinator result remain rejected CLI results and require
future watchdog coverage.

Standing authorization and host runtime bind an exact Git revision. Keep
manual approval while alert/rehearsal code is changing; review and provision
the external artifacts only after selecting the delivery boundary and freezing
the implementation revision for controlled rehearsal.

## Alert delivery custody

ADR 0040 adds `daily-eod-alert-delivery-custody/1.0` behind the intent boundary.
It is a library capability port, not an installed command or transport. A future
operator must pre-provision a dedicated owner-only `0700` alert root outside
Git, `/data`, and the daily transition run root. Repository code does not create
that root.

Custody uses a separate global lock and immutable per-deduplication-key journal.
It writes `delivery_started` before invoking an explicitly supplied transport.
A valid delivered terminal requires one external request and only a hashed
provider reference; known failure may record zero or one request. Alert journal
writes are custody evidence, never canonical Production data writes.

If the transport or process stops after the start event, do not resend. The
outcome is ambiguous and subsequent calls fail closed. A formally delivered
intent returns `already_delivered` without transport access. A known failed
terminal also requires operator review; no retry policy is authorized yet.

ADR 0041 adds a repository-only SMTP adapter behind this custody port. It is
not an installed command and remains disabled unless a separately reviewed,
owner-only external config sets `enabled=true` at the exact verified Dell
revision. Config, credential, alert root, real delivery, and scheduler state
remain absent.

The canonical `daily-eod-email-transport-config/1.0` JSON file must be `0400`
under a `0700` directory outside Git and `/data`, with its exact whole-file SHA
supplied independently. It binds the repository/data/run/alert roots, source
revision, sender, sorted unique recipients, endpoint, TLS mode, timeout, and
credential path. Only implicit TLS on 465 and STARTTLS on 587 are accepted.
Reading this config never touches the credential path.

The separate `smtp.env` must be `0400` directly under an owner-only `0700`
directory and contain exactly:

```text
TIP_SMTP_USERNAME=<external value>
TIP_SMTP_PASSWORD=<external value>
```

Never place those values in Git, shell history, logs, audit output, or a
command line. The adapter loads them only after ADR 0040 has durably recorded
`delivery_started`. Configuration/credential rejection before SMTP returns a
known zero-request failure. Once SMTP begins, any exception or partial
recipient acceptance is treated as unknown and must not be retried
automatically. Successful evidence contains only a hash of the stable
Message-ID, never a secret or raw provider response.

ADR 0043 now composes intent, custody, and SMTP in the existing one-transition
command, but only with explicit delivery opt-in. Add the following to the full
required `run-one-daily-eod-transition.sh` argument set:

```bash
--emit-alert-intent \
--deliver-alert-email \
--host-config /absolute/external/runtime/host.json \
--host-config-sha256 <64-hex-whole-file-sha> \
--email-config /absolute/external/email/smtp.json \
--email-config-sha256 <64-hex-whole-file-sha>
```

The Host Runtime and email config directories must be non-overlapping, as must
the Massive and SMTP credential directories. Email delivery does not require
data capabilities to be enabled, but both configs must match the actual clean
Dell revision and CLI data/run roots. The coordinator remains socket-guarded
unless its separate data-capability flag is enabled; SMTP is reachable only
after a formal coordinator result and non-null alert intent.

A normal result reports both `alert_intent` and `alert_delivery` as null and
does not load SMTP credentials or touch the alert root. Known email failure is
reported and exits nonzero. An exception after `delivery_started` has unknown
delivery outcome and must not be replayed; the rejected envelope still retains
the already-known coordinator status and data request/write counts. The command
remains uninstalled in real operations: first review all external paths and the
exact revision, run the ADR 0042 no-network preflight, then separately authorize
a controlled fake/local or real rehearsal.

## Joint external-control preflight

ADR 0042 provides the config-only, network-prohibited entry point:

```bash
scripts/admin/preflight-daily-eod-external-controls.sh \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --host-config /absolute/external/runtime/host.json \
  --host-config-sha256 <64-hex-whole-file-sha> \
  --authorization /absolute/external/authorization/daily.json \
  --authorization-sha256 <64-hex-whole-file-sha> \
  --email-config /absolute/external/email/smtp.json \
  --email-config-sha256 <64-hex-whole-file-sha>
```

ADR 0044 advances the result to
`daily-eod-external-control-preflight/1.1`. When email is deliberately
deferred, replace the two email arguments with the explicit flag:

```bash
--without-email
```

This returns `preflight_mode=daily_data_only`, null email/alert fields, and
`email_transport_enabled=false`. Omitting email arguments without the flag is
rejected, as is combining the flag with any email argument. Data-only mode
still requires enabled Host Runtime plus the complete active four-operation
Identity/EOD authorization; it never reads the email config or implies an
alert channel.

Run this only from the configured clean Dell source repository at the exact
revision pinned by all three artifacts. A successful result says
`configuration_consistent`; it does **not** authorize a provider request,
canonical Apply, email, rehearsal, publication, deployment, or scheduler. It
records zero credential-file access, network requests, filesystem writes, and
Production writes.

The three config directories must be distinct and non-nested. Massive and SMTP
credential directories must also be distinct from one another and from every
config/repository/data/run/alert root. The preflight intentionally does not
test credential existence or inspect their metadata. Do not pass credential
paths or values on the command line.

No real external artifacts currently exist, so this command has not been run
against an installed configuration. Its tests use only owner-only temporary
config files, absent synthetic credential paths, a fake verified runtime, and
the active socket guard.

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

1. Make a separate exact canonical-Apply authorization decision for the
   formally reviewed 2026-08-27 EOD plan.
2. Conduct a later controlled timing rehearsal to calibrate a defensible Basic
   EOD review time from non-sensitive evidence; do not treat the 30-minute
   Identity point as EOD availability.
3. Make separate authorization decisions for canonical Apply, analytics continuation,
   publication, Snapshot/bundle, OCI deployment, and finally scheduler
   activation.

The executor, journal, readiness planner, standing authorization, capability
adapters, Host Runtime, and coordinator have now had their first controlled
real use. Owner-only controls and the run root were installed at `c3af030`;
Identity fetch and canonical Apply completed, then EOD failed before package or
Apply. The next source revision invalidates those exact-revision controls.
No offline analytics action or recovery event has run. No service, timer, or
scheduler exists.

Canonical Apply reservation and no-write recovery remain available. Journal
1.3 reads the immutable 1.2 history and adds only standalone operator-review
events. ADR 0038 recovery routing remains repository-tested only; no real
recovery event was appended.
ADR 0039 alert intent is repository-tested only; no intent was persisted and no
notification delivery was attempted.
ADR 0040 alert custody is repository-tested only; no real root, transport call,
or delivery event exists. ADR 0041 SMTP config, credential loading, rendering,
TLS behavior, and custody composition are repository-tested only; no external
artifact, credential read, network call, email, service, or timer exists. ADR
0042 joint email preflight remains repository-tested only. ADR 0044's installed
data-only preflight succeeded once. ADR 0043's explicit
CLI delivery route is also repository-tested only with fake SMTP; it has not
been invoked against any real config, credential, alert root, or transport.
SMTP path remains unused.

The first installed 2026-08-27 data-only preflight succeeded at revision
`c3af030`. Identity fetch used 14 requests, its offline plan validated 13,148
provider-identity rows and 9,982 instrument/resolver rows, and one canonical
Identity Apply completed. The subsequent EOD fetch made one request and
formally ended `permanent_failure`, leaving package, staging, approval plan,
and canonical EOD targets absent. The old 1.0 terminal did not retain the
numeric HTTP status. No EOD Apply, analytics calculation, publication,
deployment, notification, or scheduler activation followed that attempt.
ADR 0047's plan-aware readiness and operator-review path are repository-tested.
One real offline review event was appended for the exact old terminal and set
a conservative 2026-08-28T16:00:00Z boundary. Its legacy HTTP status remains
unknown, and the review granted no retry authority by itself. The user later
authorized one exact EOD-only retry at `dd314db`; one request succeeded with a
12,552-result frozen package and zero Production writes. The journal ends in
`acquisition_package_ready`, readiness is `ready_for_apply_review`, and no
approval plan or canonical 2026-08-27 EOD target existed at that retry boundary.
The later offline plan now formally passes with 9,945 canonical rows, zero
duplicate business keys, zero orphan references, and two planned files totaling
1,056,432 bytes. Its file SHA-256 is
`76ac1c50a016b82772ce8ac391f8d67e107c8433caae0e1f6364b311deb23bc5`.
The target remains absent and canonical Apply remains separately unauthorized.

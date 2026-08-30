# Daily EOD Automation Control Plane

## Current scope

The daily control plane has a read-only planner, a single-action offline
executor, and separately explicit one-shot Market Intelligence and Dashboard
Snapshot Apply ports.
The planner formally reconciles one exact target session and reports one safe
next action. The executor can consume one unchanged plan fingerprint and run
only one of eleven offline daily actions under durable Dell custody: eight
analytics calculations, MI and Dashboard Snapshot approval-plan preparation,
and exact active-Snapshot serving-bundle construction. Both publication ports are absent by default and cannot be
inferred from readiness. None of these parts enables a timer.

The action order is:

```text
same-day Identity
  -> canonical EOD
  -> Phase 1a plus same-process Sector ETF Rotation audit
  -> verified-prior Phase 1b
  -> daily verified-prior Candidate
  -> Candidate entry geometry
  -> ETF relationships (Phase 2)
  -> Market Regime preview
  -> Candidate strategy channels
  -> Candidate Visual Context
  -> Market Intelligence approval plan
  -> publication review
  -> separately invoked Market Intelligence Apply
  -> Dashboard Snapshot approval plan
  -> Snapshot publication review
  -> separately invoked Dashboard Snapshot Apply
  -> exact active-Snapshot serving bundle
  -> deployment review
  -> separately enabled one-shot OCI deployment
```

Automation Plan 1.6 and Single-action Executor 1.5 add the Visual Context
stage with exact Candidate, Entry Geometry, history, panel-cache, and Oracle
bindings. A real direct-child `/tmp` rehearsal passed. The persistent workspace
is intentionally outside `/tmp`, while several older audit CLIs still enforce
direct-child `/tmp` custody. Until one shared persistent-artifact policy and a
real CLI rehearsal close that mismatch, the installed timer must remain read-
only and the unattended calculation chain must not be described as enabled.

Acquisition and canonical `/data` apply remain authorization boundaries.
Market Intelligence and Dashboard Snapshot publication are separate one-shot
authorization boundaries. Snapshot planning and bundle construction are
offline and review-only. OCI deployment is a separate default-off coordinator
capability; scheduler activation remains outside the coordinator.

ADR 0076 now adds a read-only scheduler-wake plan before any host timer. It
uses a small completion-manifest index plus a full formal reread of the latest
EOD partition, selects only the oldest missing XNYS session, and returns the
next close-plus-stabilization review time. The default candidate is disabled;
an enabled-candidate review still performs no coordinator invocation or write.

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

Installing the standing Identity/EOD ports requires
`--enable-authorized-capabilities`, an absolute
external host-config path, and its exact external whole-file SHA. The canonical
owner-only config must also enable capabilities and match the actual Dell
hostname, executing repository source, completely clean Git HEAD, current
readiness policy, data/run roots, authorization SHA, and credential path. The
credential is not read during host-runtime verification. Approved-plan and
expected-state fingerprints must be provided together before Apply.

The CLI may opt into one existing offline calculation with `--execute-offline`
or, under ADR 0069, one MI publication with all of:

```bash
--apply-market-intelligence \
--market-intelligence-approved-plan-sha256 <exact-full-file-sha256> \
--market-intelligence-expected-current-state-fingerprint <exact-inventory-sha256>
```

MI Apply also requires the externally SHA-pinned enabled Host Runtime inputs.
An approved stale-review plan additionally requires
`--market-intelligence-review-acknowledgement` with the exact acknowledgement
embedded in the plan. The acknowledgement is not written to the journal; only
its SHA-256 is retained. This mode is mutually exclusive with offline
execution, standing Identity/EOD capabilities, and unresolved recovery.
Networking remains prohibited. Default invocation continues to stop at
`review_publication`.

The CLI never loops and never gains bundle, deployment, or scheduler
authority. ADR 0038 adds mutually exclusive `--recover-unresolved`: it
formally rereads the one exact pending event and invokes only its acquisition,
canonical-Apply, offline-action, MI-Apply, or Snapshot-Apply recovery boundary. The socket
guard remains active; recovery never requests provider data, performs Apply or
linking, replays a calculation, retries, or loops. Exceptions without formal
terminal evidence report request/write counts as unknown, never as assumed
zero. ADR 0069 created no new external Host Runtime artifact, real MI Apply
invocation, service, timer, or scheduler state.

### MI Apply interruption boundary

Journal 1.4 adds `market_intelligence_apply_started` and a disjoint terminal
family. Reservation requires the unchanged `review_publication` automation
fingerprint, formal plan/candidate and whole-file SHA, current freshness or
exact plan-bound review exception, unchanged full inventory and MI consumer
pointer, and absent target/staging state. The existing publication lock then
performs the copy, target rename, and pointer compare-and-swap.

Success is journaled only after the formal active reader proves the exact
publication, target, payload/aggregate hashes, session, and planned pointer.
If the process stops or throws after the start, run only
`--recover-unresolved` with the same session and path arguments. Recovery:

- reconciles success only when that exact active state is readable;
- records not-completed only when target absence plus unchanged inventory and
  consumer state prove zero Production write; and
- blocks every inactive target, staging residue, changed state, invalid plan,
  or ambiguous outcome.

Recovery never calls Apply or `verify-then-link`. A complete inactive target
requires diagnosis and a later separately explicit existing publication
recovery procedure.

ADR 0071 separately permits one Dashboard Snapshot publication only with all
of:

```bash
--apply-dashboard-snapshot \
--dashboard-snapshot-approved-plan-sha256 <exact-full-file-sha256> \
--dashboard-snapshot-expected-current-state-fingerprint <exact-active-state-sha256>
```

Snapshot Apply requires the same externally SHA-pinned enabled Host Runtime
inputs. An approved stale-review plan additionally requires
`--dashboard-snapshot-review-acknowledgement` with the exact acknowledgement
embedded in Plan 2.4. This mode is mutually exclusive with MI Apply, offline
execution, standing Identity/EOD capabilities, recovery, and email delivery.
It does not accept MI or Snapshot Plan generation inputs and networking remains
prohibited. Default invocation continues to stop at
`review_snapshot_publication`.

### Dashboard Snapshot Apply interruption boundary

Journal 1.5 adds `dashboard_snapshot_apply_started` and a fifth disjoint
terminal family while continuing to read journal 1.2–1.4, including MI Apply
events written under 1.4. Reservation requires the unchanged Snapshot-review
automation fingerprint, formal Plan 2.4/candidate and whole-file SHA, current
freshness or exact review exception, unchanged active Snapshot state and
Activation pointer, and absent target/staging state. The existing Snapshot
publication lock then performs the staged copy, immutable target rename, and
active-pointer update.

Success is journaled only after the formal active reader proves the exact
release, target, contracts, aggregate, manifest, session, and planned pointer.
If the process stops after the start, run only `--recover-unresolved` with the
same session and artifact paths. Recovery:

- reconciles success only when that exact active Snapshot is readable;
- records not-completed only when target/staging are absent and Snapshot plus
  Activation state remain unchanged; and
- blocks every inactive target, staging residue, changed state, invalid plan,
  partial, or ambiguous outcome.

Recovery never calls Apply or `verify-then-link`. A complete inactive target
requires diagnosis and a later separately explicit existing recovery review.

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

At ADR 0042's initial implementation boundary this command had not been run
against an installed configuration. A later data-only preflight was used for
the controlled 2026-08-27 round as recorded below. Exact-revision external
controls do not remain valid after later source commits and must be reread and
separately repinned before any future capability use.

## Read-only plan

Every daily artifact path is explicit and must be a distinct direct child of
`/tmp`.
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
  --entry-geometry-audit /tmp/<current-entry-geometry> \
  --phase2-audit /tmp/<current-phase2> \
  --preview-bundle /tmp/<current-preview> \
  --strategy-channel-audit /tmp/<current-strategy-channels> \
  --market-intelligence-output-root /tmp/<new-mi-output-root> \
  --market-intelligence-approval-plan /tmp/<new-mi-plan>.json \
  --snapshot-output-root /tmp/<new-snapshot-output-root> \
  --snapshot-approval-plan /tmp/<new-snapshot-plan>.json \
  --serving-bundle-root /tmp/<new-serving-bundle-root>
```

The JSON result has one of four statuses:

- `waiting_for_authorized_input`: prepare the exact Identity or EOD catch-up;
- `ready_for_offline_calculation`: run only the named offline daily step;
- `analytics_ready`: the chain is stopped at formal MI publication review,
  Snapshot publication review, or bundle deployment review; the exact
  `next_action` identifies which one and conveys no Apply/deployment authority;
- `blocked`: stop and diagnose; do not overwrite or skip the failed boundary.

`blocked` exits 1. The other planning states exit 0 because they are valid
states, not completed actions.

## Default-off scheduler wake review

Review the next scheduler wake without installing a service or timer:

```bash
scripts/admin/plan-daily-eod-scheduler.sh \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --data-root /data/trading-intelligence-platform
```

The default reports `scheduler_candidate_enabled=false`. The explicit
`--review-enabled-candidate` flag changes only the in-memory candidate and may
propose `invoke_one_transition` when a target is ready. Both forms always
report `scheduler_installation_performed=false`, coordinator invocation count
zero, and zero
credential access, network requests, filesystem writes, and Production writes.
That field describes only the side effects of the current invocation. It does
not inspect or report whether a unit is already installed on the host. Read
actual host state through the systemd inspection commands below.

The wake planner validates the small completion manifest for every canonical
session, fully rereads only the latest EOD Parquet/Identity binding, and uses
the XNYS calendar plus the current readiness stabilization delay. It does not
assert provider completeness. Retry, interruption recovery, publication,
deployment, and alert behavior remain inside their existing coordinator/
custody boundaries and cannot be replayed by this planner.

### Repository-only pipeline-aware wake

ADR 0081 adds `daily-eod-pipeline-wake-plan/2.0` above the installed planner.
When canonical EOD is missing it preserves the existing stabilization and
oldest-gap behavior. When canonical EOD is current it requires the exact
same-session Automation Plan 1.4 and can distinguish an unfinished offline
stage from MI, Snapshot, or deployment review. An enabled candidate may only
propose one data or offline transition; every manual review and blocked state
stops.

The companion `daily-eod-workspace-layout/1.0` derives stable session paths
outside `/tmp`, canonical `/data`, and the repository. It creates nothing.
Existing direct `/tmp` children remain accepted only for historical and
controlled one-shot compatibility. No persistent root, repeated cadence,
coordinator capability, or new systemd unit is installed by ADR 0081.

Repository source now emits Automation Plan 1.6. It retains Plan 1.5's
distinct Sector Rotation audit derived beside Phase 1a, validates its exact session,
Phase 1a fingerprint, and history source, and requires MI Approval Plan 1.3 to
freeze the same audit and product fingerprints. Missing or mismatched evidence
stops at operator diagnosis; the planner does not repair, replay, publish, or
skip it. Plan 1.6 additionally requires the source-bound Candidate Visual
Context stage before MI planning. Historical Automation Plan 1.4/1.5 records
remain historical evidence.

### Repository-only bounded cadence candidate

ADR 0082 adds `daily-eod-bounded-cadence-plan/1.0`. It consumes one freshly
verified Pipeline Wake Plan 2.0 and a contiguous chain of prior distinct-wake
evidence. The default and widest candidate allows at most 16 transition wakes
over four hours, with five minutes from one completion to the next start. Each
planner process still invokes nothing. Both the cadence and pipeline candidate
must be enabled before the result can propose one invocation.

The cadence stops at manual review, blocked state, known failure, unknown
outcome, or either budget. A formally returned `no_change` may only lead to a
later fresh observation after the interval; it does not authorize replay. The
candidate creates no evidence store, runtime bridge, persistent root, service,
timer, capability, credential access, request, or Production write. Do not
bind it to the installed read-only timer.

ADR 0083 subsequently reuses the existing owner-only run journal rather than
creating a second cadence store. Journal 1.7 added standalone known-result
evidence. ADR 0084 advances the journal to 1.8 and cadence custody to 1.1: one
`cadence_wake_reserved` event is durably written before invocation, and the
matching `cadence_wake_recorded` event closes it only after a known result. The
pair retains the full enabled cadence plan and Evidence 1.2, including the
immutable cadence start, formal next-eligible time, both plan fingerprints,
result identity, timing, and budget sequence. Old 1.2–1.7 journal events and
direct 1.7 cadence evidence remain readable.

Coordinator 1.12 now preserves result meaning: provider `waiting` is waiting,
provider/ offline failure is blocked, and only formally evidenced success is
`transition_executed`. The cadence adapters project those results without
inferring hidden success.

The repository-only Pipeline Runtime 1.0 now composes one exact enabled
Pipeline plan, one exact enabled cadence plan, one reservation, one matching
data or offline capability call, and one known-result record. The default path
invokes nothing. Exceptions, invalid results, interruptions, or result-custody
failure leave the reservation unresolved; a second reservation and a later
session both fail closed. It never loops, retries, recovers, publishes, or
deploys. No CLI, real cadence event/root, capability, service, timer binding,
credential access, request, `/data` write, publication, deployment, or
Production invocation was added or performed.

ADR 0085 adds a pure Cadence Diagnosis 1.0 contract for an unresolved runtime
reservation. Given an already-read exact-session journal chain, it distinguishes
no nested action evidence, a nested action that still needs its existing
no-replay recovery, a matching formal terminal that is only ready for later
cadence-disposition review, and conflicting evidence that remains blocked.
Terminal labels are candidates rather than inferred cadence outcomes; the
diagnostic never invents a coordinator result or provider retry boundary. It
performs zero reads outside its supplied event tuple and zero writes, requests,
replays, retries, recoveries, or resolutions. No CLI or timer binding exists.

## Default-off one-transition wake bridge

ADR 0077 composes one exact unchanged enabled-candidate wake plan with one
separately supplied coordinator callable. Default review still calls nothing.
An explicit invocation calls the coordinator at most once, validates the target
and returned authority fields, recomputes the formal coordinator-result
fingerprint, retains that exact result identity, records the returned state,
and exits. Waiting, recovery-required, and alert-required results do not trigger
a second call, recovery route, or notification delivery. Malformed or
field-tampered results and results claiming scheduler, publication, or
deployment authority are rejected.

Run the credential-free synthetic five-wake rehearsal:

```bash
scripts/admin/review-daily-eod-scheduler-rehearsal.sh
```

The scenarios are current/up-to-date, oldest missing, retry waiting,
unresolved interruption, and alert required. Coordinator results are synthetic
and make no provider or Production claim. The report must show five scenarios,
four total fake coordinator calls, no more than one call per wake, no automatic
retry/recovery or alert delivery, and zero credential, network, filesystem, or
Production activity.

## Non-installed read-only systemd candidate

ADR 0078 renders exact future user-unit bytes without writing or installing
them:

```bash
scripts/admin/review-daily-eod-scheduler-systemd.sh \
  --config-id dell-read-only-wake-v1
```

The default candidate is disabled. Adding `--review-enabled-candidate` changes
only the review artifact; it does not write the user-unit directory, reload
systemd, enable/start a timer, or call the coordinator. The review requires
Dell/hui, clean `main`, an executable exact planner entrypoint, systemd 255 or
newer, a running user manager, and systemd-accepted calendar expressions. It
records exact candidate, service, and timer fingerprints.

The proposed service calls the planner without `--checked-at`, causing it to
use the current timezone-aware UTC clock. It pins that invocation to the exact
Git revision and never passes `--review-enabled-candidate`; therefore the unit
also clears inherited Python overrides, pins the project launcher and resolved
interpreter, and can only report the disabled ADR 0076 plan. Proposed New York
wake times are 13:30 and 16:30 on weekdays, covering the 30-minute stabilization
window after early and normal XNYS closes while the exchange calendar remains
authoritative.

At the ADR 0078 candidate-review boundary Dell reported a running user manager
but `linger=no`, so the enabled candidate correctly returned
`review_ready_prerequisite_missing`. ADR 0079 later records the separately
authorized user-level installation and linger change. The review command
itself still must not install units, change linger, reload systemd, or
enable/start the timer.

### Controlled read-only installation state

ADR 0079 records the separately authorized Dell installation. `hui` linger is
enabled; the owner-only user service/timer are installed, loaded, and the timer
is enabled. The first controlled start showed that this user manager cannot
apply `PrivateNetwork`, `PrivateDevices`, or explicit capability bounding.
Those directives were removed from the template and installed unit. The
remaining hardening uses a read-only filesystem view, `NoNewPrivileges`,
`AF_UNIX` restriction, the planner's socket guard, clean revision/Python
bindings, and the existing timeout.

The corrected controlled service start returned `up_to_date` through
2026-08-28 with exit status zero in about three seconds. It made zero
coordinator calls, credential accesses, external requests, filesystem writes,
or Production writes. The next checkpoint is a real calendar-triggered wake.
Do not add `--review-enabled-candidate` or any coordinator/capability arguments
to the installed unit.

ADR 0080 defines the reporting boundary after installation. Planner and
rehearsal contract 1.1 use `scheduler_installation_performed=false`; this means
the invocation did not install or alter a unit. It is not host-state evidence.
The systemd review 1.1 reports only whether that review performed installation
or activation, while the commands below remain authoritative for current host
state.

Read-only inspection:

```bash
systemctl --user status whalpha-daily-eod-wake-review.timer
systemctl --user list-timers whalpha-daily-eod-wake-review.timer
journalctl --user -u whalpha-daily-eod-wake-review.service
```

Emergency stop is reversible and does not change data:

```bash
systemctl --user disable --now whalpha-daily-eod-wake-review.timer
```

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
  --phase2-audit /tmp/<current-phase2> \
  --preview-bundle /tmp/<current-preview> \
  --strategy-channel-audit /tmp/<current-strategy-channels> \
  --market-intelligence-output-root /tmp/<new-mi-output-root> \
  --market-intelligence-approval-plan /tmp/<new-mi-plan>.json \
  --snapshot-output-root /tmp/<new-snapshot-output-root> \
  --snapshot-approval-plan /tmp/<new-snapshot-plan>.json \
  --serving-bundle-root /tmp/<new-serving-bundle-root> \
  --run-root /home/hui/.local/state/trading-intelligence-platform/daily-eod \
  --panel-cache-root /tmp/<immutable-panel-cache> \
  --candidate-work-dir /tmp/<owner-controlled-candidate-recovery> \
  --execute-action <exact-next-action> \
  --expected-plan-fingerprint <64-hex-plan-fingerprint>
```

Only `calculate_phase1a`, `calculate_phase1b_incremental`,
`calculate_candidate_daily`, `calculate_entry_geometry`,
`calculate_etf_relationships`, `build_market_preview`,
`calculate_strategy_channels`, `prepare_market_intelligence_plan`,
`prepare_dashboard_snapshot_plan`, and `build_serving_bundle` are executable.
The calculation, planning, and local-build
stages consume the same-session fingerprints already verified by their
prerequisites; they do not authorize publication or deployment.
The Candidate work directory is required only for the Candidate action. The
panel cache is optional and must remain outside `/data`.

The MI Plan action additionally requires:

```bash
--publication-created-at <explicit-UTC-timestamp> \
--publication-expected-current-state-fingerprint <64-hex-data-inventory>
```

Both values are bound into the immutable action identity. The action invokes
only Market Intelligence `--plan`, creates the two explicit `/tmp` targets,
and returns to `review_publication`. It never invokes Apply. Omit these two
arguments for the other nine actions. Recovery of an interrupted MI Plan must
reuse both exact values.

The Snapshot Plan action additionally requires:

```bash
--snapshot-generated-at <explicit-UTC-timestamp>
```

It is selectable only after the exact publication named by the formal MI plan
is active. It invokes the existing Snapshot dry-run with that active MI, the
same-session Strategy Channel audit, and the two explicit new `/tmp` Snapshot
paths. Formal completion requires current Approval Plan 2.4 and exact MI,
strategy, session, and path bindings, then returns to
`review_snapshot_publication`. It never invokes Snapshot Apply. Omit this
timestamp for the other nine actions; interrupted recovery must reuse it.

The Serving Bundle action additionally requires:

```bash
--bundle-built-at <explicit-UTC-timestamp>
```

It is selectable only after the exact pointer from Snapshot Plan 2.4 is active.
It invokes the Dell-local builder with the exact immutable V2 Snapshot path and
new `/tmp` bundle root. The source repository must be clean `main`, and the
Snapshot release suffix must identify the full current commit. The builder uses
a minimal offline frontend environment, cleans its bounded staging directory on
ordinary failure, and the formal reader then verifies every checksummed file,
the source Snapshot aggregate and bytes, contracts, analytics lineage, locales,
equal guest/credential capability, and prohibited-content flags. Completion
returns only to `review_bundle_deployment`; no OCI command exists in this
action. Omit the timestamp for the other nine actions; interrupted recovery
must reuse it.

ADR 0073's deployment mode is mutually exclusive with every other execution
mode. It requires an exact owner-only deployment-config file SHA, the reviewed
bundle path/logical fingerprint, approved remote-state fingerprint, and
expected current OCI release. One invocation performs a read-only pre-state
inspection, durable reservation, exactly one Apply command, and an independent
read-only post-state inspection. An interrupted deployment recovery performs
only the inspection and reports one external read, zero writes, and no replay.
The capability is absent when the external config is missing or disabled.
The separate `review-oci-dashboard-deployment-runtime.sh` command can render a
SHA-bound config candidate without installing it. Its default is disabled; an
explicit enabled-candidate review still grants no deployment authority and
performs zero writes or network requests.

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

1. The complete deployment path has now passed a controlled real invocation
   and independent postflight. Later source revisions still require a fresh
   exact deployment-config review and separate deployment authorization.
2. Conduct a later controlled timing rehearsal to calibrate a defensible Basic
   EOD review time from non-sensitive evidence; do not treat the 30-minute
   Identity point as EOD availability.
3. The read-only timer installation, synthetic distinct-wake rehearsal,
   owner-only cadence custody, and non-installed one-invocation runtime bridge
   are complete. Next observe a natural calendar trigger, then separately
   review a separate operator-approved unresolved-reservation disposition and
   any runtime installation.
4. Keep separate authorization decisions for acquisition/canonical Apply, MI
   publication, Snapshot, bundle, OCI deployment, and finally scheduler
   activation.

The executor, journal, readiness planner, standing authorization, capability
adapters, Host Runtime, and coordinator have now had their first controlled
real use. Owner-only controls and the run root were installed at `c3af030`;
Identity fetch and canonical Apply completed, then EOD failed before package or
Apply. The next source revision invalidates those exact-revision controls.
At that historical boundary, no recovery event or scheduled transition
service existed. The later reviewed retry, canonical Apply, and four offline
analytics actions completed as recorded below. No real recovery event was
appended. The read-only timer described above was installed later and still
performs no transition.

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
The target was absent at plan review. After the reviewed-retry custody fix at
`6256bf3`, the separately authorized apply-only transition completed with zero
external requests. The 9,945-row canonical partition formally rereads, the
journal ends in `canonical_apply_succeeded`, and the next action is offline
`calculate_phase1a`. At that Apply boundary, no analytics calculation,
publication, Snapshot, bundle, deployment, notification, or scheduler action
had followed.

The later one-transition Phase 1a action completed in 218.315399 seconds with
zero requests/writes, zero missing metrics, and zero Oracle mismatch. Its audit
fingerprint is
`887024c4847ef74a28a713c439359f3a4d8d93e49269ab58f2f0177c61159c53`.
The journal closed normally and the planner selected
`calculate_phase1b_incremental`.

The first Phase 1b invocation used the legacy Production-bound V1.0.0 prior
audit and failed closed before creating its target. The daily chain must use
the corrected stable-prefix V1.0.1 lineage, not whichever older audit happens
to back the active publication. Replanning with the formally verified
V1.0.1 2026-08-26 incremental audit produced plan fingerprint
`06da4f7f1853dfe872929f895e685c34ec020d5971d93f89ac0ac0daf395f935`.
That single action completed with audit fingerprint
`6a3a530280dbe9eea6617d76e980ed453b47e087d9e35fe588e8f7b6fe630801`,
zero Oracle mismatch, and confirmed Balanced state for both Universes. The
journal ends in `action_succeeded`, no unresolved event remains, and the next
action is only `calculate_candidate_daily`. No later stage has run.

The following single Candidate transition completed from the exact corrected
Phase 1b and verified-prior Candidate lineage. Audit fingerprint
`0fa85ae742ef47e7278c444c12f05f2082e38a5071068a5787655a11271eb4e4`
has zero Oracle mismatch and all daily prefix/restart/permutation gates true.
The action produced no `/data` or Production write and advanced the plan only
to `calculate_entry_geometry`.

This real run also exposed a control-path scaling problem. The daily business
path reached audit write in 152.944168 seconds and streaming write took
22.201208 seconds, but the journaled action took 576.027031 seconds. The
422,786,554-byte cumulative JSON audit is fully reconstructed by multiple
planner, finalization, and postcondition layers; post-plan RSS reached about
6.1 GB. ADR 0060's lighter immutable publication-evidence reader verified the
same completed custody in 1.8 seconds. Before the next large coordinated
transition, reuse an appropriately scoped custody/current-session proof at
planner and postcondition boundaries while retaining the full prior append
input read inside Candidate calculation. Do not replace exact locked plan
identity, hashes, typed current rows, or Oracle gates with existence checks.

ADR 0065 implements the planner/postcondition side of that correction. The
planner now uses completed Candidate planning evidence: it streams hashes for
the full immutable file set, checks completion/parameters/Oracle/equivalence,
and canonically validates only the small incremental lineage ledger. The
Candidate action itself continues to fully reconstruct its prior append input.
The exact 2026-08-27 plan now takes 9.45 seconds at 221,640 KiB maximum RSS,
keeps plan fingerprint
`eb19d7790605fae6d2467f6996b9411fb5fc6653f28f27b6e60c9fdd6b41811f`,
and selects only `calculate_entry_geometry` at that boundary.

The one-transition coordinator subsequently completed that Entry Geometry
action. Formal audit fingerprint
`3aa78cb694a4c06835f19fb6165cd721e62b7fe16f921240ce8a601fcd83c11a`
binds the same-session Candidate audit, assesses 1,714 / 1,827 current rows,
and passes zero-mismatch Oracle and input-permutation gates. It is shadow-only
with zero requests and Production writes. Journal event 21 is
`action_succeeded`; post-plan fingerprint
`f6fe6ddd5b4e561724088147d9dda361d270b548f2a7ff4d3df1b5b974958ff9`
has status `analytics_ready` and next boundary `review_publication`.
Publication and serving remain unchanged and separately unauthorized. The
action took 338.217438 seconds; a later optimization may avoid rebuilding the
full cumulative Candidate score history solely to select the current 3,541
records, but must preserve exact custody, typed rows, ordering, and Oracle
semantics.

The subsequent publication review exposed that the then-current
`analytics_ready` boundary meant only four coordinator-owned offline actions
were complete. The missing 2026-08-27 Phase 2/preview were completed manually
under their offline tmp-only boundaries, and the final MI Plan correctly
returned `freshness_blocked` because expected session advanced to 2026-08-28.
ADR 0067 closes that calculation-custody gap: Phase 2, preview, and Strategy
Channels are now the fifth through seventh one-transition actions. MI
publication, Snapshot, bundle, deployment, and scheduler activation remain
outside the coordinator and require their own reviews and authorizations.

The 2026-08-29 network-free review then reconciled 2026-08-28 as the oldest
missing session. The automation plan selects only `prepare_identity_catchup`;
readiness is `missed_session_recovery` / `review_fetch_authorization` because
the daily deadline elapsed. There are zero attempts and no 2026-08-28 package,
canonical target, downstream audit, or run-journal directory. No current-HEAD
external control was supplied or preflighted. The next possible boundary is
one separately authorized Identity fetch followed by its own Apply review;
EOD and every downstream stage remain out of scope until Identity completes.

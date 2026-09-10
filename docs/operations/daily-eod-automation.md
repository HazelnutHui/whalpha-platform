# Daily EOD Automation Control Plane

## Purpose and authority

This runbook describes the durable control boundaries for the post-close daily
pipeline. It intentionally does not repeat active sessions, releases,
fingerprints, or dated execution narratives.

- Read [Current Context](../project/current-context.md) for the latest verified
  operational state.
- Read [Current Status](../project/current-status.md) for the active phase,
  blockers, and next priority.
- Use dated audit files and the [changelog](../project/changelog.md) for
  execution evidence.

The Dell workstation is the source of truth for code, data, computation, and
publication preparation. OCI is only the public serving boundary. The control
plane is fail-closed and never turns planner readiness into authority.

## Durable pipeline

```text
same-session Identity
  -> canonical EOD
  -> Phase 1a + Sector ETF Rotation
  -> verified-prior Phase 1b
  -> verified-prior Candidate
  -> Candidate Entry Geometry
  -> ETF Relationships
  -> Market Regime Preview
  -> Candidate Strategy Channels
  -> Candidate Visual Context
  -> Market Intelligence plan
  -> separately authorized MI Apply
  -> Dashboard Snapshot plan
  -> separately authorized Snapshot Apply
  -> serving bundle
  -> separately authorized OCI deployment
```

The coordinator admits eleven offline actions: eight analytics calculations,
two publication-plan preparations, and serving-bundle construction. Universe
Membership candidate preparation is an independent sidecar. It neither gates
nor inherits authority from the serving chain.

These boundaries remain separate:

1. provider acquisition;
2. canonical `/data` Apply;
3. offline calculation;
4. Market Intelligence publication;
5. Dashboard Snapshot publication;
6. serving-bundle construction;
7. OCI deployment;
8. scheduler activation; and
9. alert delivery.

Completing one boundary does not authorize the next.

## Data and runtime custody

Canonical data lives only under `/data/trading-intelligence-platform`.
Persistent daily work lives under the owner-only Dell runtime workspace:

```text
/home/hui/.local/state/trading-intelligence-platform/automation/daily-eod
```

The workspace is outside Git and `/data`. Its session directories, journal,
cache, and immutable artifacts must retain their expected ownership and modes.
Do not edit, rename, copy into, chmod, or remove individual journal events.

Identity and EOD use distinct acquisition packages and Apply plans. Temporary
and persistent roles cannot be mixed. Historical `/tmp` evidence remains
readable for compatibility but is not the forward operating layout.

Every state-changing transition must:

- bind one exact session, source revision, input set, and plan fingerprint;
- hold the relevant non-blocking lock;
- record an immutable start before crossing the boundary;
- verify the formal postcondition before recording success; and
- leave ambiguous or partial outcomes unresolved for diagnosis.

## Provider readiness

Market close is not proof that the provider dataset is complete. The active
Stocks Starter policy uses the explicit profile:

```text
massive_stocks_delayed_15_minutes
```

The profile removes the earlier Basic-only availability-review requirement
after the existing 30-minute stabilization window. It does not weaken
request-count, package-quality, canonical-consistency, or publication gates.
Use the exact profile throughout readiness, custody, runtime configuration, and
scheduler review.

Readiness is network-free:

```bash
scripts/admin/plan-daily-eod-readiness.sh \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --target-session YYYY-MM-DD \
  --latest-canonical-session YYYY-MM-DD \
  --acquisition-action prepare_identity_catchup \
  --provider-recency-profile massive_stocks_delayed_15_minutes
```

Use `prepare_eod_catchup` only after same-session Identity is formally
complete. The target must be the oldest missing XNYS session. Provider failure,
rate limiting, and interruption remain governed by the bounded readiness and
acquisition-custody contracts; never poll blindly or substitute a stale
session.

## Planning and execution

### Read-only plan

`scripts/admin/plan-daily-eod-automation.sh` reconciles one exact session and
returns only one of:

- `waiting_for_authorized_input`;
- `ready_for_offline_calculation`;
- `analytics_ready`, stopped at a manual review boundary; or
- `blocked`.

All artifact paths are explicit. Persistent forward paths must come from the
same session workspace. Review the command's `--help` output and the returned
`logical_content_fingerprint`; do not reuse an earlier plan fingerprint.

### One transition

`scripts/admin/run-one-daily-eod-transition.sh` invokes the coordinator once.
Provider and canonical-Apply capabilities are absent unless exact external
owner-only controls are supplied and their whole-file hashes match the clean
Dell revision. The command never loops and does not gain publication,
deployment, or scheduler authority by implication.

The external-control preflight is network-free:

```bash
scripts/admin/preflight-daily-eod-external-controls.sh \
  --checked-at YYYY-MM-DDTHH:MM:SS+00:00 \
  --provider-recency-profile massive_stocks_delayed_15_minutes \
  --host-config /absolute/external/runtime/host.json \
  --host-config-sha256 <64-hex-whole-file-sha> \
  --authorization /absolute/external/authorization/daily.json \
  --authorization-sha256 <64-hex-whole-file-sha> \
  --without-email
```

A successful preflight proves only configuration consistency. It performs no
credential read, request, Apply, publication, deployment, or scheduler action.

### Bounded offline run

The preferred persistent-workspace entry for contiguous offline stages is:

```bash
scripts/admin/run-bounded-daily-eod-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --workspace-root /home/hui/.local/state/trading-intelligence-platform/automation/daily-eod
```

It is review-only unless `--execute` is explicitly supplied. Execution
replans before every action, preserves per-action journal custody, and stops at
provider input, publication Apply, deployment review, failure, interruption,
or its bounded action/time budget. It never requests provider data, applies
`/data`, publishes, deploys, retries, polls, sleeps, or changes a timer.

When MI-plan preparation is reachable, also supply the exact current-state
fingerprint requested by `--help`. Plan and bundle timestamps are generated
only when their stage is reached.

The single-action diagnostic entry remains
`scripts/admin/execute-daily-eod-offline-action.sh`. Use it with the exact
current plan fingerprint and complete path set shown by `--help`; it is not a
shortcut around persistent custody.

## Publication and deployment

Market Intelligence, Dashboard Snapshot, and OCI deployment each have their
own plan, review, Apply custody, and interruption recovery:

- [Market Intelligence Publication](market-intelligence-publication.md)
- [Dashboard Snapshot Publication](dashboard-snapshot-publication.md)
- [OCI Private Dashboard Deployment](oci-private-dashboard-deployment.md)
- [Deployment Boundary](deployment-boundary.md)

Serving-bundle construction is offline and review-only. A locally complete
bundle is not a deployed release. Exact current releases and source revisions
belong only in [Current Context](../project/current-context.md).

Universe Membership remains a separate candidate/Apply lifecycle:

- [Canonical Universe Membership Publication](universe-membership-publication.md)
- [Universe Pre-Activation Review](universe-pre-activation-review.md)

## Scheduler

The installed Dell user timer is intentionally read-only. It may assess the
oldest missing session and readiness but cannot call the coordinator, read
credentials, request provider data, write files, publish, or deploy. Current
host state is recorded in [Current Context](../project/current-context.md).

Read-only inspection:

```bash
systemctl --user status whalpha-daily-eod-wake-review.timer
systemctl --user list-timers whalpha-daily-eod-wake-review.timer
journalctl --user -u whalpha-daily-eod-wake-review.service
```

The repository scheduler review commands only render or assess candidates.
They do not install or enable a write-capable runtime. Unattended operation
requires separate proof of a natural wake, interruption disposition, bounded
runtime behavior, provider timing, and every existing authority boundary.

## Recovery

If a process stops after a start event, do not replay it.

- For the coordinator, use `run-one-daily-eod-transition.sh
  --recover-unresolved` with the exact original session and paths.
- For one offline action, use
  `execute-daily-eod-offline-action.sh --recover-incomplete` with the exact
  original identity.
- For acquisition, canonical Apply, publication, or deployment, follow that
  boundary's dedicated custody/runbook.

Recovery is read/reconcile-only unless its specific contract explicitly says
otherwise. It may prove success, prove no change, or remain blocked. It never
invents success, retries a provider request, replays a calculation, or repeats
an Apply.

## Alerts

Alert intent and SMTP custody exist in code, but SMTP remains unconfigured.
The absence of email delivery does not weaken fail-closed behavior; operators
must inspect blocked and unresolved states directly. Any future SMTP
configuration requires separately provisioned owner-only configuration and
credentials outside Git and `/data`, with no secret values in commands,
logs, audits, or repository files.

## Operating checklist

Before any controlled daily run:

1. Verify Dell host, clean `main`, exact revision, runtime ownership, and
   canonical data state.
2. Read [Current Context](../project/current-context.md) and identify the
   oldest missing XNYS session.
3. Run the network-free planner and review its exact next action.
4. Cross only the separately authorized boundary for that action.
5. Reread formal postconditions and journal state.
6. Stop on stale inputs, path drift, partial state, unknown outcome, or any
   mismatch.
7. Replan before the next action.

After a complete guarded chain, record material operational evidence in one
dated audit and update current context/status once. Do not append the execution
narrative to this runbook.

## Historical evidence and governing decisions

The removed dated narrative remains available in Git history and in the
authoritative evidence records:

- [2026-09-06 Complete-Chain Audit](../audits/daily-eod-publication-deployment-2026-09-06.md)
- [2026-09-09 Runtime Workspace Activation](../audits/daily-eod-runtime-workspace-activation-2026-09-09.md)
- [2026-09-09 Provider Access Probe](../audits/massive-current-session-access-probe-2026-09-09.md)
- [2026-09-09 Publication and Deployment Audit](../audits/daily-eod-publication-deployment-2026-09-09.md)
- [Project Changelog](../project/changelog.md)

The detailed contracts are governed by the accepted ADR sequence, especially
ADRs 0030–0047, 0065–0085, 0095–0097, 0150, 0154, 0180–0190. Read the
[ADR index](../decisions/README.md) rather than copying their full rationale
into this operating entry point.

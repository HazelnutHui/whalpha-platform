# ADR 0037: Gate One-Transition CLI with Host Runtime

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0036 supplies authorized capability callables, but the repository still
lacked an operational entry point and an independently controlled way to decide
whether those callables may be installed. Passing a revision, hostname, or
authorization path directly from an ordinary scheduler command would let the
caller merely assert the safety facts it is supposed to prove.

## Decision

Add external contract `daily-eod-host-runtime-config/1.0` and a one-transition
CLI. Absence of the host config, `capabilities_enabled=false`, or omission of
the CLI's explicit enable flag leaves both authorized capability ports absent.

The host config is a canonical owner-only file in a pre-provisioned directory
outside Git and `/data`. Runtime also requires its exact whole-file SHA-256 from
separate host configuration. It binds:

- Dell hostname;
- source repository root and implementation revision;
- canonical data root and run-journal root;
- authorization directory, artifact path, and external authorization SHA pin;
- credential path without reading or exposing its contents; and
- the exact readiness-policy fingerprint.

Before installing capabilities, the CLI proves the executing Python source is
inside the configured repository, derives the actual short hostname, reads the
actual local Git HEAD, requires a completely clean worktree including untracked
files, and recomputes the current readiness-policy fingerprint. It does not
trust those values merely because the host config contains them.

The CLI accepts explicit exact-session paths and invokes the coordinator once.
It never loops. Without capability enablement it installs a socket guard and
can only plan, report manual authorization/recovery state, or run one separately
opted-in ADR 0030 offline action. Capability enablement requires all of:

1. the explicit invocation flag;
2. an absolute external host-config path and whole-file SHA;
3. an owner-only canonical host config with `capabilities_enabled=true`;
4. verified actual host/source/clean revision/policy identity; and
5. the independently pinned standing authorization when a capability is called.

Approved-plan SHA and expected-state fingerprints are optional at fetch stages
but must be supplied together before an Apply stage can reserve anything.
If an invoked boundary raises without formal terminal evidence, the CLI reports
request/write counts as unknown rather than falsely asserting zero.

This repository work creates no host config root or artifact, authorization
artifact, SHA pin, credential read, provider request, run root, `/data` write,
publication, deployment, notification, service, timer, or scheduler.

## Consequences

- The executable entry point remains useful in manual/default-deny mode.
- A config file cannot activate capabilities without both an external SHA pin
  and explicit invocation enablement.
- A clean configured repository cannot authorize code executed from another
  checkout or a dirty revision.
- Scheduler installation still grants no publication or deployment authority.
- At this decision's acceptance, unresolved acquisition, Apply, or offline
  attempts were reported but not executed. ADR 0038 subsequently added the
  explicit bounded recovery route required before a controlled rehearsal.

## Alternatives Considered

### Trust revision and hostname command-line strings

Rejected because the process must derive actual runtime identity independently.

### Install capability ports whenever an authorization artifact exists

Rejected because authorization scope and operational installation are separate
controls.

### Loop until analytics or publication readiness

Rejected because one wake-up must never share authority across several data or
calculation transitions.

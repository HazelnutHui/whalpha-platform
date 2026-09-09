# ADR 0188: Bind Paid Provider Recency Through the Daily Chain

## Status

Accepted

## Date

2026-09-09

## Context

The owner supplied a Massive dashboard confirmation that Stocks Starter was
successfully purchased on 2026-09-09. Current official plan material describes
that tier as 15-minute delayed. The repository already modeled a delayed
provider-recency profile, but administrator and scheduler entry points still
constructed the default Basic end-of-day policy. A paid account would therefore
continue to encounter the Basic-only initial EOD operator-release gate.

Provider plan is operational configuration, not market-data identity. Existing
canonical records use the historical `massive_stocks_basic` provider identifier;
renaming those records merely because the account tier changed would rewrite
stable lineage without improving the underlying facts.

The purchase confirmation establishes the intended account tier but does not
prove live API entitlement, same-evening completeness, or aggregate finality.
The first completed-session use must remain controlled and observed.

## Decision

Keep Basic as the backward-compatible library and CLI default, and make the
selected provider-recency profile explicit across the complete daily boundary:

- readiness review and one-transition coordinator CLIs;
- coordinator and acquisition configuration;
- acquisition reservation, outcome, and recovery reconstruction;
- canonical Apply readiness reconstruction;
- host-runtime verification and external-control preflight;
- scheduler, pipeline-wake planning, and synthetic scheduler rehearsal; and
- immutable read-only systemd service candidates.

The selected policy fingerprint is included in acquisition and Apply custody
inputs. A reservation made under one profile cannot be recovered or completed
under another profile. The external host runtime and standing authorization
must carry the same policy fingerprint as the invocation.

For Stocks Starter, the explicit profile is
`massive_stocks_delayed_15_minutes`. It removes only the special Basic initial
EOD availability review after the existing 30-minute post-close stabilization
window. It does not remove oldest-session-first ordering, request limits,
backoff, quality checks, package custody, exact Plan/Apply, downstream
publication reviews, or the statement that provider completeness is not
asserted.

Retain the existing canonical provider identifier for lineage compatibility.
Treat it as a legacy adapter/storage namespace, not a current subscription-tier
claim. Any future provider-ID normalization requires a separate migration
decision.

No API request, credential read, `/data` write, scheduler installation,
publication, deployment, or Production change is authorized by this decision.
Before the paid profile becomes operational, rebuild the exact-revision
external pins and observe one completed live session through the existing
custody and quality gates.

## Consequences

- The paid plan can be used without bypassing or weakening the daily state
  machine.
- Basic remains testable and usable as an explicit rollback profile.
- Plan changes become visible in policy fingerprints and immutable scheduler
  unit bytes rather than hidden account assumptions.
- Existing external host/authorization artifacts and the installed detached
  read-only timer remain unchanged until separately rebound to a committed
  revision and selected profile.
- Marketing recency is still not treated as a guarantee of final EOD data.

## Alternatives Considered

### Change the global default to Starter

Rejected because account entitlement is external configuration and the
repository must retain a safe Basic fallback.

### Infer the plan from the API key or a failed request

Rejected because credentials must not be inspected for product metadata and an
HTTP result does not reliably identify the account tier.

### Keep passing a delayed policy only in ad hoc Python calls

Rejected because reservation, recovery, Apply, host verification, and timer
planning could then disagree about the governing policy.

### Rename all historical provider identifiers

Rejected because the plan change does not change source identity and a broad
canonical migration would add risk without user value.

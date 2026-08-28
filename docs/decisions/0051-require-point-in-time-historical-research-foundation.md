# ADR 0051: Require a Point-in-Time Historical Research Foundation

## Status

Accepted

## Date

2026-08-28

## Context

The retained canonical sequence has 29 EOD sessions and same-session Identity
snapshots, but it has no daily Universe Membership publication, canonical
corporate-action dataset, governed adjustment ledger, or complete
instrument-lifecycle history. Every retained bar carries unverified all-one
adjustment factors. Current constituents therefore cannot be projected
backward for performance evaluation, and a disappearing instrument cannot be
reliably distinguished from a delisting, merger, ticker transition, or source
omission.

ADR 0050 already separates sealed signals from later outcomes and requires
point-in-time membership. A source-neutral historical foundation is required
before physical evaluation datasets or strategy formulas can be selected.

## Decision

Adopt the requirements in
[Historical Research Data Foundation V1](../architecture/historical-research-data-foundation-v1.md).
The foundation keeps six governed families separate:

1. raw, unadjusted canonical EOD bars;
2. point-in-time Instrument/Provider Identity observations;
3. daily Universe membership decisions and their evaluated base;
4. canonical corporate-action facts and revisions;
5. instrument lifecycle, ticker history, lineage, and terminal-status facts;
6. derived, explicitly based adjustment ledgers.

A seventh manifest layer binds coverage and fingerprints without becoming a
second copy of the facts.

Every historical fact distinguishes when it applies, when the source made it
knowable when that timestamp exists, and when Dell ingested it. Backfilled
facts with unknown historical availability cannot become signal features.
Unknown or ambiguous membership, lineage, action, or adjustment evidence is
quarantined rather than converted to a negative decision or a neutral factor.

The canonical foundation remains provider-neutral, stable-ID keyed, Parquet-
first, immutable by completed revision, and physically owned by Dell. OCI does
not acquire, govern, or recompute history. Existing raw OHLC is never rewritten
to incorporate an adjustment. Corporate-action facts and derived adjustment
factors remain separate.

The acquisition floor remains 252 contiguous completed XNYS sessions; 504 is
the preferred first research target. Session count alone never grants
performance eligibility: feature warm-up, forward-outcome maturity, membership
coverage, lifecycle coverage, adjustment reconciliation, and quarantine rates
must also pass. Until a separate deletion policy is accepted, canonical facts,
superseded revisions, and completion manifests have no automatic expiry.

No provider is selected as the exclusive source. The repository-evidenced
capability matrix is recorded in
[Historical Research Source Capability V1](../providers/historical-research-source-capability-v1.md).
Documented availability is not live entitlement verification.

This decision authorizes no provider request, credential access, `/data`
write, physical backfill, formula, evaluation dataset, publication, Snapshot,
deployment, scheduler, or deletion.

## Consequences

- A 252- or 504-session bar download is not mistaken for a valid historical
  research panel.
- Membership and lifecycle gaps become visible completeness failures rather
  than silently dropped rows.
- Ticker changes normally preserve one stable instrument, while uncertain
  mergers and successors remain quarantined.
- Adjustment methodology can be corrected through a new immutable revision
  without mutating raw bars or historical research evidence.
- Existing 29-session data remains mechanically useful but is still not
  performance eligible.
- The next step is a bounded provider/entitlement and physical-storage plan,
  followed by a separately authorized small pilot rather than a bulk backfill.

## Alternatives Considered

### Backfill EOD first and repair membership later

Rejected because current-constituent replay would make early results appear
usable and encourage parameter selection before survivorship controls exist.

### Treat provider-adjusted prices as the canonical historical series

Rejected because split adjustment, dividends, raw chart prices, total return,
identity transitions, and terminal outcomes are different facts with different
revision semantics.

### Store everything in one research table

Rejected because it would mix observations, canonical facts, methodology
decisions, adjustments, and future labels, weakening auditability and making
look-ahead leakage harder to detect.

### Introduce a database or distributed data platform now

Rejected because the Dell Parquet/manifest boundary is sufficient for the
current scale. A database threshold remains a later operational decision.

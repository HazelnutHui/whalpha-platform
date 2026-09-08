# ADR 0173: Separate current and research classification evidence

- Status: Accepted
- Date: 2026-09-08

## Context

The product needs formal Sector/Industry membership before Candidate
concentration, sector breadth, sector-stratified research, or Defensive
Rotation can be interpreted professionally. Canonical Identity and the current
Massive bulk adapter do not contain that taxonomy. ETF price relationships are
analytical proxies, not security membership.

Official public material shows several plausible sources. Massive Ticker
Overview exposes SIC on a single-ticker endpoint, but its documented SEC
report-period date behavior can expose information before the filing was
submitted. S&P GICS History explicitly advertises a four-level point-in-time
taxonomy with from/thru dates. LSEG TRBC advertises deeper hierarchy and history
from 1999. FactSet RBICS offers useful operating-footprint and revenue exposure.
None has been sampled, licensed, permission-cleared, or acquired for this
project.

An effective classification date alone does not prove when a classification
was knowable. A company-level assignment also does not automatically prove a
listed-security membership.

## Decision

Use one canonical Classification V1 boundary while assigning separate
eligibility to current display and historical research.

1. External taxonomy observations remain provider-specific evidence. They
   retain external entity/security IDs, taxonomy/version/code, business-valid
   interval, source availability, provider revision/update time, Dell
   observation time, and permission-review identity.
2. Canonical membership is keyed by stable `instrument_id` and canonical
   `classification_id`. A provider company assignment may reach a security only
   through an explicit reviewed projection. Ticker and name never create a
   positive match.
3. Current display may use a completed latest-as-of dataset after stable-ID
   resolution, taxonomy mapping, missing/ambiguous counts, and equal
   guest/credential display permission pass. It is labelled current and is not
   backfilled.
4. Historical research additionally requires defensible source availability
   at or before the signal cutoff, historical interval completeness, revision
   semantics, and inactive coverage. Missing availability makes the row
   ineligible for research regardless of its valid-from date.
5. S&P GICS History is the first specification/sample inquiry candidate because
   its four-level hierarchy matches the accepted canonical structure and its
   public dataset description explicitly identifies point-in-time from/thru
   dates. This is evaluation order, not source selection, purchase authority,
   entitlement, or license approval.
6. LSEG TRBC is the second candidate. RBICS is deferred for complementary
   product/revenue exposure rather than the first traditional taxonomy. Massive
   SIC may be tested only as a current coarse diagnostic; it cannot become
   formal historical classification.
7. The provider-neutral contract, fixtures, persistence, and fail-closed reader
   may be implemented before source selection. A live adapter, acquisition,
   `/data` publication, Candidate integration, Snapshot, and deployment remain
   separately gated.

## Consequences

- A useful current classification can reach the product without contaminating
  historical research.
- Later paid sources expand or replace source observations without rewriting
  stable instruments or vendor-locking analytics.
- Availability-time leakage, current-membership backcasting, ticker-only joins,
  issuer/security collapse, and ETF-proxy mislabelling fail closed.
- Missing classifications remain a visible unknown bucket rather than being
  silently dropped from concentration denominators.
- Source procurement is now a concrete external dependency, but contract and
  fixture implementation can continue on Dell without waiting for a purchase.

## Rejected alternatives

- **Use Massive SIC everywhere:** coarse filer classification, single-ticker
  request shape, and report-period date semantics do not meet the historical
  boundary.
- **Use the latest vendor taxonomy for all 304 sessions:** creates survivorship
  and look-ahead bias around reclassifications, new listings, and inactive
  issuers.
- **Treat ETF relationships as Sector membership:** price relationship and
  company classification answer different questions.
- **Wait to design until a vendor is purchased:** would let vendor field names
  define the canonical model and make replacement unnecessarily disruptive.

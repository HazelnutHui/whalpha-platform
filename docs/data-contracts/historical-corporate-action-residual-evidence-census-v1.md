# Historical Corporate Action Residual Evidence Census V1

## Purpose

Contract `historical-corporate-action-residual-evidence-census/1.0` joins the
remaining unresolved five-year Corporate Action observations to already
retained lifecycle, inactive-security, and official FINRA OTC evidence. It is
a quarantine diagnostic, not an identity resolver.

## Inputs and lineage

The builder formally reads and binds:

- one immutable Corporate Action Resolution Shadow;
- its immutable unresolved-ticker census;
- one or more explicitly ordered inactive-lifecycle shadow anchors; and
- one sealed FINRA OTC Daily List range and its complete package chain.

The manifest records physical and logical identities for each input boundary,
the clean implementation revision, evaluation time, exact source denominator,
and output identities.

## One-to-one result

`records.parquet` contains exactly one row per unresolved typed Corporate
Action source observation, keyed by source action ID and source revision. Each
row retains the provider ticker, effective date, action type, and exact-date
resolution failure reason.

Candidate relations use these mutually exclusive states:

- `inside_canonical_observed_span`;
- `unverified_terminal_gap` between last observation and provider delisting
  candidate;
- `before_canonical_first_observed`;
- `after_delist_candidate`;
- `mixed_anchor_boundary`; or
- `no_lifecycle_evidence`.

Inactive-provider evidence records only ticker-match shape, provider type
codes, and whether zero, one, or multiple stable source identifiers are
present. FINRA evidence records exact-date/symbol occurrence count, exact
numeric occurrence count, and explicit lifecycle-related flags. All lists and
rows are deterministic and canonically ordered.

## Authority limits

The contract does not assign `instrument_id`, infer ticker ownership, accept a
provider delisting date as a last tradable date, interpret opaque FINRA event
codes, resolve dividend basis, or create a canonical action or lifecycle fact.
It grants no Adjustment Ledger, Historical Coverage, research admission,
analytics, Candidate, Production, or deployment authority.

The immutable package is a direct `build=*` child of an owner-only custody
root. It contains exactly `records.parquet` and `manifest.json`; directories
are mode `0700`, files are mode `0400`, overwrite is refused, and physical plus
logical fingerprints are formally reread.

See [ADR 0220](../decisions/0220-cross-census-residual-corporate-action-evidence-without-assignment.md).

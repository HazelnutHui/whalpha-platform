# ADR 0135: Reconstruct Legacy ETV Identity Semantics by Explicit Version

- Status: Accepted
- Date: 2026-09-04

## Context

The ADR 0134 census found 221 custody-valid packages whose rebuilt Instrument
Master and ticker Resolver families match the accepted same-day snapshots but
whose provider Identity family does not. Four representative row-level checks
found a single difference: before ADR 0124, provider type ETV was represented
as rejected `unknown_provider_type_etv`; current code represents the same
non-instrument observation as excluded `exchange_traded_vehicle`.

ADR 0124 explicitly applies the current rule prospectively and requires any
historical normalization to use a separately versioned derived mapping. The
current builder must not be weakened or changed back merely to reproduce old
immutable snapshots.

## Decision

Add an explicit historical comparison profile named
`pre_etv_governance_v1`, separate from the default `current_v1` profile.

The legacy profile starts from the current, fully validated package build and
may change only a provider Identity row that already satisfies all of these
conditions:

- `resolution_status=excluded`;
- `resolution_method=unresolved`;
- no canonical instrument ID;
- `quality_status=warning`;
- the sole quality flag is `exchange_traded_vehicle`.

Such a row is projected to the exact prior representation:

- `resolution_status=rejected`;
- `quality_status=rejected`;
- sole quality flag `unknown_provider_type_etv`.

The Instrument Master and Resolver tuples remain byte-for-byte logical inputs.
The build summary moves the same count from expected exclusions to malformed
rejections, from the `excluded` category to `malformed`, and into the ETV
unknown-type count. Every other field and count is unchanged.

No creation timestamp or session-date heuristic chooses this profile. It is
explicitly requested and succeeds only if all three reconstructed family
fingerprints equal the formally inspected accepted snapshot. A mismatch in any
other field remains a mismatch.

The existing current-builder census becomes contract 1.1 and records the
requested rebuild profile. `current_v1` remains the default. A legacy census is
separate evidence and cannot overwrite or relabel the original current-profile
report.

## Consequences

- Current ETV governance, classification, Universe disposition, and future
  Identity publication remain unchanged.
- Historical packages can prove equivalence to the immutable rule version that
  originally produced their accepted snapshot without pretending the old
  classification is current policy.
- ETV remains absent from Instrument Master and Resolver under both profiles;
  the compatibility profile cannot make it Universe eligible.
- If the full legacy census does not account for every one of the 221
  Identity-only mismatches exactly, unexplained sessions remain blocked and
  require a new review rather than a broader transformation.
- The operation remains network-disabled, read-only, `/tmp`-only, and without
  Historical Coverage or research authority.

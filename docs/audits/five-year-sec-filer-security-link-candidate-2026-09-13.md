# Five-Year SEC Filer-to-Security Link Candidate — 2026-09-13

## Result

The complete rolling five-year SEC filer-to-stable-security link candidate is
retained in owner-only Dell custody. It preserves one explicit decision for
every canonical Instrument Master row across all 1,255 XNYS sessions from
2021-09-13 through 2026-09-11.

This is an identity-link candidate, not an issuer master or fundamental feature
panel. It does not authorize projecting one SEC filer's facts to every linked
security or share class.

## Bound inputs and time semantics

- implementation revision:
  `650f5e363b7b8f152cbec966aea169989db34845`;
- canonical Instrument Master and Provider Identity: 1,255 / 1,255 sessions;
- retained Provider Identity source evidence: 1,253 sessions; and
- explicitly missing and quarantined source sessions: 2026-08-13 and
  2026-08-19.

Every session is bound to its exact Instrument, Identity, and source manifests,
Parquet hashes, content fingerprints, and observed-time evidence. The result
contains 952 `eligible_at_source_observed_at` sessions, 301
`outcome_reconciliation_only` sessions, and two `source_custody_missing`
sessions. `eligible_at_source_observed_at` does not backdate a reconstructed
relationship to the historical session; a downstream query must still compare
the retained observation time with its registered signal cutoff.

## Decision census

| Decision | Rows |
| --- | ---: |
| Admitted unique CIK link | 9,456,209 |
| Quarantined missing CIK | 1,205,516 |
| Quarantined missing source custody | 19,879 |
| Conflicting CIK | 0 |
| Identity mismatch | 0 |
| **Total stable-security decisions** | **10,681,604** |

The input Provider Identity observations separately account for 10,681,613
resolved rows, 1,084,664 unresolved, 1,965 ambiguous, 77,204 rejected, and
2,799,736 excluded rows. Input identity-row counts can exceed stable-security
decision counts because a security may retain more than one provider identity
occurrence.

The manifest records 197,182 session-local multi-security CIK groups. This is
not a unique issuer count and does not select a primary share class. Every
output row retains `issuer_projection_authorized=false`.

## Custody and verification

- package:
  `historical-source/sec-filer-security-link-candidate/build=five-year-20260913-v1`;
- files / bytes: 1,256 / 758,604,458;
- directories: 1,256;
- manifest bytes: 1,956,575;
- manifest SHA-256:
  `2a432ff2ca92fdc912ba5712b7487feb905fc24d562e5f84301e3e98f86d3ab0`;
- logical fingerprint:
  `a71a6180f86228b7c80062c121da42e46a101d8f012e7f7a537147be0b609c71`;
- permissions: directories `0700`, files `0400`; and
- symlink / partial / temporary residue: zero / zero / zero.

The build used eight worker processes for session materialization, then the
existing strict single-process formal reader validated every input and output
partition. It completed in 56 minutes 16.11 seconds, used 7,246.61 aggregate
user CPU seconds, and peaked at 423,776 KiB resident memory. The long tail is
the full formal reread, not network, rate limiting, or repeated acquisition.

An independent lightweight postflight revalidated the canonical manifest,
aggregate denominators, four boundary/exception partitions, schemas, physical
hashes, authority flags, file inventory, ownership, modes, and residue state.
The focused link suite passes four tests, including exact cleanup of a failed
build's own partial directory.

The complete API suite passes 2,608 tests in 266.01 seconds with the two
unchanged dependency deprecation warnings.

## Authority and next boundary

Canonical-data, Membership, analytics, publication, deployment, and scheduler
write counts are zero. Research performance and issuer projection remain
unauthorized.

The next fundamental gate is an explicit share-class projection policy plus a
small registered concept/unit/period/form query set. A query must reject or
quarantine missing source-time eligibility and one-to-many CIK ambiguity; this
candidate cannot be treated as permission to broadcast filer facts across all
linked securities.

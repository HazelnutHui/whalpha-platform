# ADR 0145: Collapse Exact-Duplicate Identity Index References

- Status: Accepted
- Date: 2026-09-05

## Context

The 2026-08-31 canonical-source Membership shadow failed the unchanged 0.999
provider-evidence linkage gate. The source and all three accepted Identity
families reconstructed exactly, so this was not a source-custody mismatch.

The accepted Identity snapshot contains eight provider rows marked
`exact_duplicate`. Each pair has the same ticker, resolution status, canonical
instrument, and stable identifiers. Instrument Master construction already
retains one Instrument and one ticker Resolver for each pair, but the later
security-evidence index preserved both identical `IdentityReference` values.
The evidence resolver therefore treated an identical pair as a non-unique
stable identifier and withheld eight otherwise deterministic joins.

Two other 2026-08-31 observations, AREN and PAAI, share stable identifiers but
are distinct unresolved Identity references. They are genuine collisions and
must remain quarantined.

## Decision

Deduplicate only structurally identical `IdentityReference` values while
assembling provider-identity indexes. Equality includes ticker, canonical
instrument, resolution status, share-class FIGI, composite FIGI, and provider
instrument ID.

Do not merge references merely because they point to the same canonical
instrument. Any difference in ticker, status, or stable-identifier fields
continues to make the index non-unique and follows the existing collision or
ambiguity path.

Keep the 0.999 linkage threshold and every existing localizable-collision rule
unchanged.

## Consequences

- Exact provider duplicate rows cannot create a false downstream collision.
- Genuine multi-reference identifiers remain visible and fail closed.
- The change applies equally to formally loaded and in-memory accepted
  Identity snapshots because both use the shared index assembler.
- 2026-08-31 must be rerun from canonical source and compared against the
  expected two-collision boundary before it can join the temporary shadow.
- This decision does not publish Membership, fill the two missing source
  dates, establish historical knowledge time, or change research readiness.

## Verification

- The corrected 2026-08-31 build maps 9,965 of 9,967 join-eligible
  observations, retains two genuine collisions, passes the unchanged gate at
  0.999799337815, and produces 19,930 temporary Membership decisions.
- All 303 accepted Identity partitions contain exact duplicates on only
  2026-08-31 and 2026-09-03. The corrected five-session boundary changes no
  business decision on 8/28, 9/1, or 9/2. On 9/3 only FAN changes in both
  Universes from false-collision quarantine to explicit ETF exclusion.
- Independent 8/31 and 9/3 single-session outputs are byte-identical to the
  corrected batch outputs. All 2,067 backend tests pass.
- No external request, `/data` or Production write, publication, deployment,
  or scheduler change occurred.

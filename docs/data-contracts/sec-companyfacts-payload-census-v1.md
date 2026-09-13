# SEC Company Facts Payload Census V1

## Purpose

`sec-companyfacts-payload-census/1.1` proves that every member of one sealed
SEC Company Facts package was fully decompressed, CRC-checked, parsed, and
structurally inventoried. It is a source-quality report, not a fundamental
dataset.

## Source and range binding

The report binds the source snapshot date, source manifest SHA-256, source
logical fingerprint, archive SHA-256, member-name fingerprint, member count,
and exact evaluation date range. Payload-read members must equal source
members. Every member must reconcile to exactly one of populated, exact empty
JSON object, structurally valid empty-`facts` placeholder, or quarantined.

Archive read or CRC failure stops the entire census. Invalid JSON, invalid CIK
root identity, missing issuer name/facts root, and malformed namespace,
concept, or unit containers quarantine the affected member. An empty `facts`
object with filename-bound CIK is retained as an empty source placeholder even
when SEC supplies no entity name; it is not mislabeled as corruption. A malformed fact
item inside an otherwise valid unit is counted as a fact-level residual and
does not erase unrelated valid facts.

## Census content

The sealed report contains:

- total and in-range valid facts and unique accession counts;
- filed-date population before, inside, after, or invalid for the range;
- duration/instant, amendment, frame, value-type, field-presence, form, and
  unit counts;
- per-namespace entity, concept, and fact counts;
- unexpected root, concept, and fact fields; and
- exact quarantined member names/reasons and malformed fact-item count.

Ordered counts and quarantine records are deterministic. Valid fact counts
must reconcile across filed-date, duration/instant, value-type, unit, and
namespace dimensions. The output is JSON, mode `0400`, in an owner-only mode
`0700` root, and is capped at 16 MiB.

## Authority boundary

The report fixes `acceptance_timestamp_count=0`,
`filed_date_same_day_eligibility=false`, and source availability to
`date_only_pending_accession_acceptance_join`. It records zero normalized,
canonical, analytics, publication, deployment, and scheduler writes.

Presence in the SEC archive proves neither historical listed-security
identity nor knowledge at a signal timestamp. CIK is a filer key. Later
normalization must preserve each source occurrence, and a later SEC
submissions join must establish accession acceptance time before conservative
session eligibility is assigned.

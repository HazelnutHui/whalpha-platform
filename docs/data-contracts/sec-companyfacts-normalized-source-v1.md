# SEC Company Facts Normalized Source V1

## Purpose and grain

`sec-companyfacts-normalized-source/1.0` preserves every admitted in-range SEC
Company Facts occurrence with its conservative filing clock. It is a
source-normalized family, not a current-value table or a listed-security
fundamental.

The package has three row types:

- entity: one per populated source member;
- concept: one per source CIK/namespace/concept; and
- occurrence: one per source member/namespace/concept/unit/unit-array ordinal
  whose filed date lies in the exact range.

## Occurrence fields

Each occurrence retains source member and CIK, namespace/concept/unit,
ordinal, source occurrence ID, raw fact fingerprint, parsed start/end/filed
dates plus original optional fiscal/frame fields, numeric value kind and
canonical numeric text, accession, form, filing-clock admission state,
selected source-available UTC timestamp, eligible XNYS session, clock and
normalization reason codes, and an unresolved instrument state.

Integers and decimals remain distinct. Numeric text is derived with exact
decimal parsing; downstream code must not convert values to binary float by
default. The raw sealed source remains authoritative for original JSON bytes.

## Partition and integrity

Occurrence artifacts are partitioned by `filed_year` and deterministic worker
part. Entity and concept catalogs use the same worker partition. Artifacts are
mode `0400` under a mode-`0700` package. The final manifest binds:

- Company Facts source and payload census;
- filing-clock package manifest and content fingerprints;
- implementation revision, exact range, worker count, and Arrow schema
  fingerprints;
- per-artifact kind/year/part/row count/bytes/physical SHA/logical fingerprint;
- source occurrence, clock admission, value kind, namespace, form, and quality
  counts; and
- zero stable-identity, canonical, analytics, publication, deployment, and
  scheduler authority.

Completed publication is partial-directory first and atomic rename last.
Formal reread validates every artifact and reconciles occurrence count exactly
to the Company Facts payload census in-range count.

## Admission boundary

An occurrence with a filing-clock row may be source-time admitted even when
the clock preserved an acceptance or filed-date warning. An occurrence whose
accession is one of the three missing Submissions rows remains physically
present as `quarantined_missing_filing_clock` with no invented timestamp or
session. Any malformed normalized value remains a separate explicit
quarantine reason.

All rows have `instrument_resolution_status=unresolved` and null
`instrument_id`. No CIK or current ticker may fill that field.

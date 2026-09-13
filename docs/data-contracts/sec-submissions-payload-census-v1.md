# SEC Submissions Payload Census V1

## Purpose

`sec-submissions-payload-census/1.1` measures exact filing-clock coverage for
the in-range Company Facts accession population. It is a source reconciliation
artifact, not a normalized filing ledger.

## Binding and read completeness

The report binds physical and logical identities of the sealed Company Facts
source, final payload census, and sealed Submissions source. The Company Facts
accession extractor must reproduce the final census count. Every Submissions
member must be fully decompressed, CRC-checked, JSON-parsed, and assigned to a
validated root, validated historical shard, validated placeholder, or exact
quarantine record.

Root members require filename/root CIK agreement plus `{filings: {recent,
files}}`. Historical shards are direct columnar filing objects. Every nonempty
filing object requires accession, filing date, acceptance datetime, and form
arrays; all columns must be arrays of identical length. Unknown columns are
counted rather than dropped.

## Coverage output

The report reconciles:

- total filings by range relation, accession validity, acceptance validity,
  and form;
- root/shard/placeholder and quarantine counts;
- root file references against actual shard members;
- current ticker/exchange array state and former-name record count without
  historical projection;
- target accessions matched/missing, repeated across filing rows, carrying a
  valid or conflicting acceptance value, and agreeing/disagreeing with Company
  Facts filed dates; and
- deterministic fingerprints of the complete missing target set and matched
  accession-to-acceptance mapping, plus at most 100 sorted missing samples.

The mode-`0400` JSON output lives in a mode-`0700` owner-only root and is capped
at 16 MiB. Ordered counts and samples are deterministic.

## Authority boundary

The report accepts only the SEC archive's exact
`YYYY-MM-DDTHH:MM:SS.sssZ` UTC representation and fixes the acceptance state
to `sec_utc_timestamp_pending_market_session_mapping`; same-day eligibility
remains false. Contract 1.0's compact/local-time assumption is superseded and
its diagnostic output is not an admissible input. The report records zero
stable instrument resolutions,
normalized filing/fact writes, canonical writes, analytics, publications,
deployments, and scheduler changes. A later normalized filing-clock contract
must make the conservative market-session mapping before any fundamental can
be admitted at a signal time.

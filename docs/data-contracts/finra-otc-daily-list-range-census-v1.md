# FINRA OTC Daily List Range Census V1

## Purpose

This network-free contract proves that every exact monthly FINRA source
package in a declared range can be reread transitively. It records coverage,
content identity, event counts, data versions, and repeated source identifiers
without converting source rows into canonical lifecycle facts.

## Contract

| Field | Value |
| --- | --- |
| Contract | `finra-otc-daily-list-range-census/1.0` |
| Provider | `finra_otc_daily_list` |
| Evidence role | `official_otc_corroboration_only` |
| Network requests | zero |
| Canonical writes / analytics / publication / deployment | zero |

The reader derives the exact sequence of partial and full calendar-month
partitions from `range_start` and `range_end`. Every package must exist at its
contract name and pass the source-package V1 reader. The census then binds all
package manifest hashes, logical fingerprints, data versions, request counts,
row counts, and retained page bytes into one package-chain fingerprint.

## Repeated source identifiers

`OTCDailyListID` is required but is not assumed globally unique. Every
repeated identifier is retained with each date, source location, event code,
symbols, and full-row fingerprint. `complete_with_repeated_identifiers` means
all physical partitions are complete while at least one source identifier has
multiple occurrences; it is not a lifecycle conflict resolution.

Downstream normalization must use the located occurrence fingerprint and
event semantics. It must not silently deduplicate by `OTCDailyListID`, select
the latest row, or infer that a repeated identifier is necessarily an error,
correction, or supersession without further evidence.

## Sealed census

An exact census may be sealed once as
`range-census=START--END.json` beside the packages. The file is owner-only,
mode `0400`, bounded to 1 MiB, and refuses overwrite. Formal reread validates
the complete typed contract and logical fingerprint.

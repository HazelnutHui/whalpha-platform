# FINRA OTC Daily List Source Package V1

## Purpose

This contract retains a complete, exact-date slice of the official FINRA OTC
Daily List as source evidence. It is deliberately not a canonical lifecycle or
corporate-action publication.

## Contract

| Field | Value |
| --- | --- |
| Package contract | `finra-otc-daily-list-source-package/1.0` |
| Page contract | `finra-otc-daily-list-source-page/1.0` |
| Checkpoint contract | `finra-otc-daily-list-source-checkpoint/1.0` |
| Provider | `finra_otc_daily_list` |
| Partition | One exact, non-reversed interval inside one calendar month |
| Page limit | 500 |
| Maximum pages / records | 100 / 50,000 |
| Response / retained page ceiling | 3 MiB / 4 MiB |
| Package ceiling | 256 MiB |
| Minimum request interval | 1.0 second, serial |
| Automatic retry | none |
| Evidence role | `official_otc_corroboration_only` |

The selected field list is the complete 60-field metadata set observed from
the official endpoint on 2026-09-10. Its ordered fingerprint is stored in
every completed manifest. Unknown response fields fail closed so a provider
schema change cannot silently alter meaning.

## Invariants

- `calendarDay` must fall inside the exact package interval.
- `OTCDailyListID` must be present and positive.
- Request offset and response offset must agree.
- Record total and data version remain constant within a package.
- The retained row count must equal the provider record total at completion.
- Repeated source identifiers within the package are counted, never silently
  removed. `OTCDailyListID` is not assumed globally unique across packages.
- Every page is mode `0400`; package directories are owner-only `0700`.
- Page hashes, request fingerprints, counts, observation times, checkpoint,
  manifest, and the exact file set are formally reread.
- Request IDs, cookies, credentials, authorization material, and raw response
  headers are not retained.

## Time and semantic boundary

`calendarDay`, event dates, and `dailyListDatetime` are source fields.
`source_observed_at` is Dell's retrieval time. Historical retrieval does not
prove when an event was first available to a strategy; source availability is
therefore `unverified` until separate evidence establishes it.

The source may support later provider-neutral observations after stable-ID
resolution. It must not directly establish Membership, current eligibility,
major-exchange lifecycle completeness, successor lineage, terminal
consideration, last-tradable date, or return adjustments.

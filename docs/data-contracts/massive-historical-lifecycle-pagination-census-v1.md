# Massive Historical Lifecycle Pagination Census V1

Contract: `massive-historical-lifecycle-pagination-census/1.0`.

The census follows at most six inactive All Tickers pages for one exact anchor,
at 1,000 rows per page, zero retry and serial 15-second pacing. It preserves the
same safe pagination and aggregate-only evidence rules as Lifecycle Coverage
Probe 1.0, but has a distinct exact acknowledgement.

`completed` means only that `next_url` disappeared within the ceiling.
`truncated_at_ceiling` means more pages remain. Both deny lifecycle-completeness,
Historical Pilot, data-write, publication and performance authority.

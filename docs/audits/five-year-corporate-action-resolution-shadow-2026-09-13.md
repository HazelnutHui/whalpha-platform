# Five-Year Corporate-Action Resolution Shadow Audit — 2026-09-13

## Scope

This audit records the first complete ADR 0217 resolution shadow for the
retained Massive baseline split and dividend observations from 2021-08-11
through 2026-09-09. The successful Dell run used clean main revision
`74ee01c14fd957e6495341610244c648c006aa67`, prohibited network access, treated
`/data` as read-only, and wrote only the explicitly selected owner-only private
candidate root.

An earlier run on revision `244740c6de6f22f3be7aba8d680b59b193200ab1`
stopped after 11.70 seconds because seven dividend rows had missing or invalid
provider tickers and could not enter the existing typed row. It left no target
or staging residue. The contract was then tightened to account for such rows
in a separate hashed quarantine artifact rather than dropping them or
fabricating tickers.

## Bound inputs

- Split baseline: 6,491 rows; manifest SHA-256
  `79920fb7f53d5fa912c8e2186aa0e1ee1aaa8108e5be9c17008dc65e8a34633c`;
  logical fingerprint
  `d3d13fef5b3f54f20916cb43ce7f19f03565b34326b0d17f8590a0c9d9871bfd`.
- Dividend baseline: 235,751 rows; manifest SHA-256
  `48fa9a818507bdb88044214d62e98a0ceb2709282957ec821abe65a28d7ab5eb`;
  logical fingerprint
  `016e5b4744856fa7bc9573424504ea273cb053147fd277d08ea58c4ee66cbfc5`.
- Reconciled-edition Identity evidence: 1,234 sessions from 2021-09-13
  through 2026-08-12; logical fingerprint
  `faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`.
- Rolling Identity evidence: 304 sessions from 2025-06-23 through 2026-09-04;
  logical fingerprint
  `d2225da8d4ffd2b7e83ff98b72f75647503690a2aff2c87731c00b115b65fefb`.
- The evidence union contains 1,251 unique sessions. All 287 overlaps bind
  identical complete artifacts; overlap conflicts are zero.

The separate full repeat remains revision evidence. Its five removed and five
added split IDs have identical non-ID economic payloads and are not collapsed
or promoted by this shadow.

## Result

All 242,242 source rows are accounted for. A total of 242,235 entered typed
Corporate Action Source Observation partitions; seven dividend rows with
`missing_or_invalid_ticker` entered the separate unrepresentable quarantine.
Typed mapping is therefore explicitly not one-to-one, while complete source
accounting is one-to-one.

| Outcome | Count |
| --- | ---: |
| Resolved / active typed rows | 129,086 |
| Unresolved / quarantined typed rows | 113,149 |
| Exact event-date Identity available | 238,379 |
| Exact event-date Identity unavailable | 3,856 |
| Exact-date ticker unresolved | 109,293 |
| Invalid provider historical adjustment factor flags | 12 |
| Unrepresentable missing/invalid ticker rows | 7 |

Resolved counts are 126,848 cash dividends, 1,781 reverse splits, 195 stock
dividends, and 262 stock splits. Unresolved counts are respectively 108,896,
2,629, 852, and 772. Every typed row remains marked
`source_available_time_unavailable`; the result is outcome reconciliation
only.

## Custody and performance

The private candidate is
`historical-source/corporate-action-resolution-shadow/build=20260913-v1`
beneath the Dell owner state root. It contains 14 files / 17,110,708 bytes and
11 directories. Every file is mode 0400, every directory is mode 0700, and
there are zero symlinks or hidden staging entries. Its relative file/hash-list
fingerprint is
`83dec79d692dc64210c812a226a23f9315adbcb011ecaa8bcda229e539252869`.

The shadow manifest SHA-256 is
`794fea3f843092186db90e410f8c106037b2425801de193dd8729a178ee2c883`;
its logical fingerprint is
`c71e0e481d83a23161f7130e45a55eac0e4895345108440b15d627232f1dfac1`.
The seven-row quarantine is 2,894 bytes with SHA-256
`6de4030f097b4ee6818e8026db7cff3b4ba8f3c885c3fe4cfd4a09f37f35034d`.

Build plus built-in reread completed in 488.33 seconds with 3,949,844 KiB
maximum resident memory. A separate formal output and Identity-binding reread
completed in 41.10 seconds with 1,367,472 KiB maximum resident memory.

## Authority and remaining gates

This result improves source accountability and exact-date stable-ID coverage;
it does not complete the five-year database. The 113,149 unresolved typed rows,
seven unrepresentable rows, source-ID instability, unavailable historical
source timestamps, missing exact-date sessions, incomplete lifecycle/terminal
outcomes, absent-event neutrality, canonical event semantics, and complete
price/volume adjustment factors remain explicit gates.

The next bounded diagnostic should classify unresolved tickers across the
complete bound Identity history without assigning them: zero historical
candidate, one stable candidate, or multiple candidates. That census may guide
official/free evidence work, but only separately governed event-date or
lifecycle evidence may promote a resolution.

No provider request, canonical `/data` write, Historical Coverage change,
analytics execution, Candidate input, publication, deployment, or scheduler
change occurred.

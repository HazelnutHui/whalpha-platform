# Five-Year Corporate-Action Unresolved Census Audit — 2026-09-13

## Scope

This audit records the first ADR 0218 assignment-free census of every
unresolved typed row in the retained five-year Corporate Action Resolution
Shadow. The Dell run used clean main revision
`214047ba0a996d86548ad8431fd74d98da2b1f2f`, eight spawned workers, prohibited
network access, treated `/data` as read-only, and wrote only the explicitly
selected owner-only private census directory.

The census does not repair or assign an action. It measures whether each
unresolved provider ticker appears against zero, one, or multiple stable
`instrument_id` values anywhere in the 1,251 Identity sessions already bound
to the resolution shadow.

## Bound inputs

- Resolution-shadow manifest SHA-256:
  `794fea3f843092186db90e410f8c106037b2425801de193dd8729a178ee2c883`.
- Resolution-shadow logical fingerprint:
  `c71e0e481d83a23161f7130e45a55eac0e4895345108440b15d627232f1dfac1`.
- Source denominator: 242,242 rows; 242,235 typed and seven separately
  unrepresentable.
- Census population: all 113,149 unresolved typed rows / 13,931 normalized
  provider tickers.
- Identity evidence: 1,251 unique sessions from 2021-09-13 through
  2026-09-04. Every session Resolver was formally scanned. Resolver binding
  fingerprint:
  `c1db08edbe692d910bf0276291c2a03d7412b66680eda932299a57a0c15e8427`.

## Result

| Historical candidate class | Distinct tickers | Source rows |
| --- | ---: | ---: |
| Zero candidates | 11,433 | 89,074 |
| One candidate | 2,456 | 23,879 |
| Multiple candidates | 42 | 196 |
| Total | 13,931 | 113,149 |

Zero-candidate tickers are 82.07% of the ticker population and 78.72% of
unresolved rows. One-candidate tickers are 17.63% and 21.10%, respectively.
Multiple candidates are 0.30% of tickers and 0.17% of rows. The census retains
2,540 ticker/stable-ID relations covering 2,515 distinct candidate
instruments. Stable-ID assignments remain exactly zero.

By action type, the unresolved population contains 108,896 cash dividends,
2,629 reverse splits, 852 stock dividends, and 772 stock splits. The full
action-type/class and exact-date-failure/class matrices are retained in the
manifest.

## Temporal interpretation

The candidate classes do not authorize event-date resolution:

- Of 23,879 one-candidate rows, only 253 fall inside that candidate's observed
  first/last session span. A total of 6,514 precede it and 17,112 follow it.
  Therefore 98.94% of this class still lacks even a continuous observation-
  span basis for an event-date claim.
- Of 196 multiple-candidate rows, 111 fall inside the combined candidate span,
  77 precede it, and eight follow it. Ticker reuse remains explicit.
- The 3,856 exact-date-Identity-unavailable rows split into 3,394 before the
  bound range, 343 on the two later trading sessions 2026-09-08 and
  2026-09-09, and 119 on holidays or other non-session dates inside the range.
  The 343 tail rows are the only immediate exact-session evidence-extension
  opportunity. Non-session events require governed effective-dated lifecycle
  evidence, not a nearest-session fallback.
- The remaining 109,293 rows had an exact Identity session but no matching
  ticker. Of these, 87,189 have zero history-wide candidate, 21,939 have one,
  and 165 have multiple candidates. This is primarily a security-scope and
  lifecycle evidence problem, not a missing-price-history problem.

## Custody, performance, and recovery

The private package is
`historical-source/corporate-action-unresolved-census/build=20260913-v1`
beneath the Dell owner state root. It contains two files / 3,842,904 bytes.
The directory is mode 0700 and both files are mode 0400; ownership is `hui`,
with zero symlinks and zero partial residue.

- Manifest SHA-256:
  `321662e3b692370fb2b83b8c0550ac8388ed16a71f54442961c582c829ec4192`.
- Logical fingerprint:
  `0dd861364c083e0e54b4d3d6a76a0fd5eacb14ae125490ffb111a3ec984b0296`.
- Candidate-record file SHA-256:
  `2b2366c97c587a15fb47f6454d29759e33efc9131d22dac3d8df1276e46337d0`.
- Candidate-record logical fingerprint:
  `b38aeeae72fe12be8c0981bfaa73caafd4e89b4cf2649b6171a40d4fb7cba833`.

The first build plus mandatory full Resolver readback completed in 183.59
seconds at 449% average CPU and 2,468,872 KiB maximum resident memory. A
supported CLI idempotency rerun completed in 184.26 seconds, returned
`already_present`, reproduced every count and fingerprint, and preserved the
directory and both files' inode, size, modification time, and modes exactly.

One additional ad-hoc reader attempt from Python standard input stopped before
the parallel scan because the `spawn` multiprocessing mode cannot reload a
`<stdin>` main module. It did not alter the package. The documented module CLI
is the supported operator entry and subsequently passed the complete zero-
write rerun.

Focused corporate-action/lifecycle regression passed 89 tests. The complete
API suite passed 2,586 tests with the same two dependency deprecation warnings.

## Next boundary

Do not auto-promote the 2,456 unique historical candidates. First bind the
already available exact Identity sessions for 2026-09-08 and 2026-09-09 and
remeasure their 343 tail rows. Then use effective-dated security/lifecycle
evidence to investigate the much larger exact-session ticker-absent and
outside-candidate-span populations. A paid cross-venue source remains a
measured-gap option, not an assumed prerequisite.

No source record, stable ID, canonical `/data`, Corporate Action, Adjustment
Ledger, Historical Coverage, analytics, Candidate, publication, deployment,
or scheduler state changed.

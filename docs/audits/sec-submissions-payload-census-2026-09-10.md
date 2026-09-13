# SEC Submissions Payload Census — 2026-09-10

## Scope

Fully read the sealed SEC Submissions snapshot and reconcile its filing clocks
to the exact 172,265-accession Company Facts population filed from 2021-08-11
through 2026-09-09. The operation was network-free, used eight Dell workers,
and changed no `/data`, canonical family, analytics, Product, Production,
deployment, or scheduler state.

The initial run used clean revision `b07496b` and exposed an incorrect compact
local-time parser assumption. Direct source inspection proved the official
archive uses millisecond UTC values. Contract 1.1 corrected that assumption at
clean revision `6f00f72` and ran into a distinct owner-only output root. The
contract-1.0 output is retained only as superseded diagnostic evidence.

## Structural result

Every one of 989,553 ZIP members was decompressed, CRC-checked, JSON-parsed,
and classified without quarantine:

| Member state | Count |
| --- | ---: |
| Valid root members | 984,189 |
| Valid historical shards | 5,363 |
| Valid exact placeholder | 1 |
| Quarantined members | 0 |

The members contain 27,217,476 filing rows. All rows have a valid accession,
filing date, and exact `YYYY-MM-DDTHH:MM:SS.sssZ` acceptance value; 6,119,488
filing rows are within the support range. All 5,363 root shard references are
present. One structurally valid shard is not referenced by its current root;
that discrepancy remains explicit and does not invalidate independent rows.

## Company Facts reconciliation

| Measure | Count |
| --- | ---: |
| Company Facts target accessions | 172,265 |
| Matched in Submissions | 172,262 |
| Missing from Submissions | 3 |
| Matched with a valid acceptance value | 172,262 |
| Accessions repeated across submission rows | 17,845 |
| Accessions with more than one distinct acceptance value | 107 |
| Exact Company Facts/Submissions filed-date sets | 172,247 |
| Filed-date disagreements | 15 |
| Matched targets without a filing date | 0 |

The three missing target accessions are
`0001193125-26-386466`, `0001477932-26-003313`, and
`0001558370-23-006754`. Their complete set is fingerprinted in the sealed
report. No missing value was inferred from filing date, CIK, or current issuer
metadata.

Repeated accessions are not automatically errors because one filing can occur
in more than one filer/member context. The 107 acceptance conflicts and 15
filed-date disagreements require explicit conservative normalization; they
were not resolved by arbitrary first-row selection. Current root ticker and
exchange arrays remain reconciliation-only and cannot be projected backward.

## Sealed result and verification

The final mode-`0400` contract-1.1 report has physical SHA-256
`6ab8e3970cf05b4af964833d82af93aa9444a372f1cb79ffa5a378c811e2c249`
and logical fingerprint
`bfa416ca41003e163932b8c0185386ea4fd5d9a461146274918dfbadb7c41004`.
Formal reread passed. The superseded contract-1.0 report has physical SHA-256
`6190446bb7610c38bf3aab62fc66a77e9f725397513b0c2d913e24e3c89584c9`
and logical fingerprint
`74aec84818fc2d8b5c23aeb0f284818094ad8b18212591ca1234a957a9a539f3`;
its zero-valid-acceptance count is known invalid and grants no authority.

The focused Company Facts/Submissions tests passed seven cases and the full SEC
provider suite passed 236 cases before the live run.

## Alignment decision

Filing-time source coverage is now measured and nearly complete, but no
fundamental is signal eligible yet. The next stage must create a source-bound
filing-clock ledger, preserve all distinct values and row provenance, use the
latest conflicting acceptance as the conservative earliest admission bound,
quarantine missing accessions, map availability to a separately versioned
XNYS session rule, and still keep CIK-to-stable-security resolution separate.

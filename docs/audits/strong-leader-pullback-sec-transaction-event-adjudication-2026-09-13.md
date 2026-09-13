# Strong-Leader Pullback SEC Transaction Event Adjudication Audit — 2026-09-13

## Verdict

Typed issuer transaction-completion evidence is complete for all 61
first-strategy cases previously linked to an in-window common-equity Form 8-K.
Every document produced one unique completion date under the frozen ruleset;
ambiguous and unsupported counts are zero.

This is private source evidence, not a canonical listing-lifecycle or terminal
fact. Termination reason, consideration, parties, tradability, terminal return,
Historical Coverage, and research admission remain unresolved.

## Bound inputs

- implementation revision:
  `5f8eb9cd70e0c47b79050e7a3ccaf7476a9ca2fe`;
- immutable 219-request plan and complete source package;
- 89-document form-aware transaction-candidate package;
- 61-match point-in-time SEC cover adjudication; and
- evaluation time: `2026-09-13T21:35:42Z`.

The builder made no network request and required exact prior report, source,
raw-byte, normalized-text, stable-ID, accession, and cover-decision identities.

## Scope and rules

Sixty documents used an explicit introduction plus Item 2.01. One THR document
used a bounded implicit pre-item completion paragraph plus Item 2.01. Any
intervening Item 1.01, 1.02, or other section was excluded.

| Selected rule | Cases |
| --- | ---: |
| Named Closing Date in introduction | 30 |
| Dated transaction-completion statement | 29 |
| Explicit closing-of-merger date | 1 |
| Dated tender acceptance followed by effected merger | 1 |

The highest supported rule had to yield one unique date. No case date was
hard-coded and no lower-priority rule was used to override ambiguity.

## Cover-date counterexamples

Fifty-two completion dates equal the inline-XBRL cover report date. Nine are
later, proving that cover date cannot serve as the event date:

| Request | Ticker | Cover date | Completion date |
| ---: | --- | --- | --- |
| 11 | OLO | 2025-09-11 | 2025-09-12 |
| 45 | MTSR | 2025-11-12 | 2025-11-13 |
| 68 | DAWN | 2026-04-22 | 2026-04-23 |
| 90 | TMHC | 2026-07-20 | 2026-07-24 |
| 104 | VERV | 2025-07-23 | 2025-07-25 |
| 109 | RNAM | 2026-02-26 | 2026-02-27 |
| 115 | TPH | 2026-05-13 | 2026-05-14 |
| 147 | FYBR | 2026-01-16 | 2026-01-20 |
| 200 | CFLT | 2026-03-16 | 2026-03-17 |

The selected event range is 2025-07-24 through 2026-08-17.

## Artifact and reread

The owner-only output is:

`/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-transaction-event-adjudication/adjudication=20260913-v1`

- report SHA-256:
  `acf4b350e89d56bbb9ac32bfcd906cec08c66721d5d5661994ab5ed68a0fd237`;
- logical fingerprint:
  `89d4c7388aa7e47d1609fcadee3d388e9d4f342d1ff4da02b76c113528e3d510`;
- directory/file modes: `0700/0400`; and
- symlinks, partial files, staging files, and temporary residue: zero.

An exact second invocation returned `already_present` with the same identities.

## Verification and authority

- eight focused tests passed;
- the complete API suite passed 2,672 tests with two unchanged dependency
  warnings;
- wrapper syntax, module compilation, and repository diff checks passed; and
- network requests, termination-reason decisions, consideration decisions,
  party decisions, first/last tradability, lifecycle facts, terminal outcomes,
  `/data` writes, Historical Coverage writes, research admissions, Candidate
  writes, publications, deployments, and scheduler changes: zero.

## Next gate

Use the 61 typed issuer events to adjudicate termination reason, consideration,
and predecessor/successor/acquirer relations. Keep exchange trading cessation,
effective delisting, last tradability, and terminal returns in their separate
market-status and price-evidence stages. LNW, REVG, and SAND remain quarantined.

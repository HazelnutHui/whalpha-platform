# Strong-Leader Pullback Trading Cessation Adjudication Audit — 2026-09-14

## Verdict

The fixed 61-case first-strategy population now has reproducible, private
evidence comparing SEC-stated trading-stop boundaries with formal canonical
EOD presence by stable `instrument_id`.

- 45 cases state a before-open boundary;
- eight state an after-close boundary;
- eight do not prove an exact stop time and remain `unsupported`;
- 52 explicit cases match the expected final EOD session and next-session
  absence; and
- one case is `conflicting` rather than coerced into agreement.

This is not a complete first/last-tradability or legal-delisting result. The
sampled eight-field coverage matrix remains 244 / 512 matched.

## Inputs and implementation

- implementation revision:
  `ef6dee53bb9e308bc38bdd94a23e62f01a3612a7`;
- source-acceptance sample SHA-256:
  `17a1c177be65693786a410c1c2107c499e34a88960541a24339644e12ba01416`;
- Form 25 candidate SHA-256:
  `c634eaa46a4d143810f2e24c51d7192a48f83a590b6c8b54b353f48563b2c099`;
- termination-reason SHA-256:
  `c3ef6f8a0e51def3419b07d7f1303105a00df9e693ec4c6cbb0a2c4c1434224d`;
- party-relation SHA-256:
  `a44dff5ace2ef6dc9b7cb8487b2bc529732522f215caa482299f0b8c4cd2176a`;
- ruleset fingerprint:
  `cf310f96de519fe7af8d0cd9368cd34bb891b1fa154b24042151935bca31e626`;
- 114 unique canonical EOD sessions, selected-session fingerprint:
  `d1f968e9b11d8e89609149c4ccd12e43236a68afb4adf4ac3f7f6aa377715501`.

The 114 sessions are the deduplicated union of three-session contexts around
the 53 explicit boundaries. Every selected partition was formally reread with
its historical Identity binding. Ticker was never used as the historical join
key.

## Retained conflict

Request sequence 90, stable instrument
`62620f34-d002-5b43-a731-70f6679ea04e`, is the sole conflict. The SEC source
states an after-close boundary on 2026-07-24, while canonical EOD last observes
the target on 2026-07-23. The retained Massive raw response for 2026-07-24 also
contains no TMHC row, so the discrepancy was not introduced by dropping a
present provider row during canonical mapping.

The result preserves the difference as provider absence or possible no-trade
uncertainty. It does not infer an earlier legal delisting date or manufacture a
zero terminal return.

## Output and verification

The immutable private report is:

`/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-trading-cessation-adjudication/adjudication=20260914-v1/trading-cessation.json`

- report bytes: 177,817;
- report SHA-256:
  `694e8b01274fdcad9bef2e0178e805df994f2526c190598b665e965541c2fae9`;
- logical fingerprint:
  `40b9ab103837a01e77131355c41c72a15317354f3e7c4f19807a3ea4f8747301`;
- custody/output/report modes: `0700` / `0700` / `0400`;
- exact rerun: `already_present` with identical hashes;
- partial directories and symlinks: zero.

Four new focused tests, 13 linked focused tests, and the complete 2,694-test
API suite passed. The suite retained two unchanged dependency warnings.

The formal read took roughly two and a half minutes because the existing
canonical reader verifies every selected EOD partition and historical Identity
snapshot. This is finite and acceptable for evidence construction. Reader
optimization is not required for the lifecycle gate and was intentionally not
opened as a new workstream.

## Authority retained at zero

The report records 53 observed-last-EOD evidence cases, including the retained
conflict, but zero first-tradable dates, legal delisting-effective dates,
complete first/last-tradability fields, complete suspension/delisting fields,
canonical lifecycle facts, terminal outcomes, strategy triggers, forward
outcomes, performance metrics, canonical `/data` writes, Historical Coverage
writes, research admissions, Candidate writes, publications, deployments, and
scheduler changes.

Next work should normalize the terminal payoff only for cases supported by the
typed consideration evidence and resolve successor or consideration-issuer
identity only where that payoff requires it. Unsupported timing and the three
unlinked lifecycle cases remain explicit quarantine rather than a reason to
build an unrelated global entity master.

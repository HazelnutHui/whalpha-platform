# Strong-Leader Pullback Terminal-Population Trading Cessation Adjudication Audit

Date: 2026-09-14

## Scope

Independently compare the corrected-population SCS Item 3.01 realized trading-
halt statement with formal stable-ID EOD presence. The operation was zero-
network, read only three canonical EOD sessions, and did not read credentials,
write `/data`, create a legal-delisting or lifecycle fact, value consideration,
create an outcome, admit research, publish Candidate data, deploy, or modify a
scheduler.

## Result

- output: `adjudication=20260914-v1/trading-cessation.json`
- implementation revision: `81e4a5886cbfc7732b958409b3dc1144320267a4`
- evaluated at: `2026-09-14T08:00:00Z`
- stable instrument ID:
  `ff8ae3f6-a3ae-5127-983b-0f94386f0055`
- source-stated trading-stop boundary: before the 2025-12-10 open
- expected and observed last EOD session: 2025-12-09
- next exchange session: 2025-12-10
- resolution: `matched`
- report SHA-256:
  `8a94a697249735e05d0a861b4e8ad62dac50f1a7218d5fb75f841c339a263048`
- logical fingerprint:
  `342bbafdcf797efd3ef13eae0ab4b96b2d7c25a5d6d4c98ac1c518098ba299eb`
- selected-session fingerprint:
  `a9e3bc6d4e8833600287ac726e93158f7b3e69fe5ac1daa41dca6f384aca382c`

The selected canonical sessions contain 9,108, 9,112, and 9,125 records.
SCS is present on 2025-12-08 and 2025-12-09 and absent on 2025-12-10. Each
partition formally verified its bound historical Identity snapshot.

## Preserved limitations

- last retained EOD observation is not proof of an intraday last execution;
- first tradability and legal delisting effectiveness remain unsupported;
- holder election, automatic adjustment/proration, listed consideration
  identity, normalized payoff, and terminal reference value remain unresolved;
- terminal-gap census V2 remains 42 / 65 securities and 196 / 302 five-session
  paths with reference evidence; and
- lifecycle fact, terminal outcome, performance, and research-admission counts
  remain zero.

## Verification

- exact replay returned `already_present` with the same SHA-256 and logical
  fingerprint;
- custody and output directories are `0700`, the report is `0400`;
- no symlink, partial, or staging residue was found;
- five focused tests, eleven linked tests, and the complete 2,770-test API
  suite passed with two unchanged dependency deprecation warnings; and
- network, canonical write, Historical Coverage, Candidate, publication,
  deployment, and scheduler counters remain zero.

## Next bounded gate

Adjudicate the SCS holder-election and automatic-adjustment/proration policy
before assigning any listed consideration identity or terminal reference
value. Do not silently choose the cash, mixed, or stock election.

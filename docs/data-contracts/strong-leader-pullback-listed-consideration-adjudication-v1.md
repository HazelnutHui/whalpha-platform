# Strong-Leader Pullback Listed-Consideration Adjudication V1

## Purpose

`strong-leader-pullback-listed-consideration-adjudication/1.0` resolves only
the candidate stable identity of listed common-share merger consideration in
the 12 frozen source cases. It does not calculate market value or return.

## Inputs

The network-disabled operation formally rereads:

- the exact 12-case source plan;
- all 12 source artifacts and document hashes; and
- the terminal-payoff report containing one normalized listed-equity ratio per
  case.

The plan binds each source accession to a candidate SEC filer CIK and one
event-time canonical common-security `instrument_id`. The source package binds
the exact retained bytes. Any changed binding fails closed.

## Evidence gate

Each decision requires a bounded source span that agrees on:

- merger transaction and target common security;
- consideration ordinary/common share class;
- exact exchange ratio, compared as normalized decimal text; and
- the SEC filer CIK to canonical common-security identifier chain already
  frozen in the plan.

Only a decision with all four matches receives the proposed stable ID. Company
names and tickers remain locators and never independently grant identity.

## Resolution states

- `matched`: all four elements agree and one candidate stable ID is assigned;
- `final_exchange_ratio_absent_from_registration_source`: the file proves the
  transaction, target, consideration class, and a variable ratio formula, but
  not the later exact ratio;
- `transaction_registration_scope_absent`: the selected 424B3 is not a merger
  share-registration document; and
- `required_evidence_not_matched`: the deterministic expected evidence profile
  cannot be reproduced.

Every record retains source and normalized-text hashes, ratio occurrence count,
evidence offsets/text/hash, individual gate booleans, reasons, assignment
state, and zero authority counters. The report reconciles all resolution and
assignment counts and is immutable in owner-only `0700/0400` custody.

## Authority boundary

The report creates at most a first-strategy consideration-security evidence
assignment. It creates no terminal value, canonical lifecycle fact, strategy
outcome, `/data` or Historical Coverage write, research admission, Candidate
result, publication, deployment, or scheduler change.

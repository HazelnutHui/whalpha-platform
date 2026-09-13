# ADR 0222: Use Path-Local Split Bases for Strategy Features and Labels

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0221 reduced the first Strong-Leader Pullback action problem to 44 exact
event-date resolved split-like exposures and one unassigned reverse-split
candidate relation. All 44 resolved source actions already exist as active
canonical split facts. The existing sparse Adjustment Ledger projects affected
raw EOD rows to the fixed 2026-09-04 basis and marks all rows associated with
these events clear. That ledger was built for outcome reconciliation and
explicitly denies point-in-time eligibility and absent-row neutrality.

The registered V2 development estimand is a split-adjusted underlying-stock
price return. Feature paths end at the signal close, while labels begin at the
next-session open. Applying a later global basis directly as a historical
signal input would introduce unnecessary future-event lineage even where a
ratio happens to be invariant. Treating every omitted sparse-ledger row as a
factor of one would separately invent missing-event neutrality.

## Decision

1. Future V2 feature construction will use a path-local signal-session basis.
   For each raw source session `s` in `t-20..t`, compose only canonical active
   split-like actions satisfying `s < effective_date <= t`. Price fields use
   the exact product of `from / to`; volume uses its reciprocal. No action
   after `t` enters a feature factor.
2. Future label construction will use the label exit session as its local
   basis. For a next-session-open entry on `t+1` and close exit on `t+h`, only
   actions satisfying `t+1 < effective_date <= t+h` mechanically cross the
   return. An action effective on `t+1` is retained as entry-boundary event
   context because the open is already on the post-action basis; it is not
   silently applied as a second factor.
3. Cash dividends remain event and risk context. They do not adjust the V2
   price-return label and do not turn it into shareholder total return.
4. A path crossing a canonical quarantined action, unresolved possible impact,
   unassigned action relation, or unproved lifecycle/terminal boundary remains
   quarantined. Price discontinuities may falsify coverage but never create an
   inferred action.
5. The fixed-basis sparse Adjustment Ledger remains required reconciliation
   evidence for known split arithmetic, but it is not the V2 feature or label
   adapter. A later adapter must derive path-local factors from canonical facts
   and bind the exact action coverage accepted for that path.
6. No dense global factor-one table will be built. Missing-event neutrality
   must be proven by source coverage and conflict evidence, not by absence from
   the current sparse ledger.
7. The existing V1 signal-eligible input contract is not changed. This decision
   applies only to the future ADR 0193 development V2 path and grants no
   development, outcome, metric, Historical Coverage, Candidate, publication,
   or Production authority.

## Evidence

The network-free formal cross-read found:

- all 44 exact resolved exposures match active canonical split facts: 11
  reverse splits, 20 stock dividends, and 13 stock splits;
- their existing fixed-basis ledger paths contain 6,859 clear rows and zero
  quarantined rows: 1,739 / 2,999 / 2,121 by the same action types;
- their feature-window relation count is 722, exactly matching the prior
  development census's clear split-exposure count;
- the one unassigned reverse split matches the canonical publication's
  possible-impact quarantine and touches 12 feature paths; and
- exact resolved split-like action/path relations number 33 at the one-session
  label boundary, 99 through three sessions, and 165 through five sessions.
  The 33 `t+1` relations are entry-boundary context; the later-window
  mechanical crossing relations remain subject to path-local construction.

These results prove consistency for known event arithmetic. They do not prove
that the current action source has no missing events.

## Consequences

- Known split math no longer needs another global ledger or another broad
  rescan.
- The future feature adapter cannot depend on action knowledge after the
  signal session merely because a fixed later basis is numerically convenient.
- The future label adapter has an explicit next-open event boundary and cannot
  double-adjust an action effective on the entry session.
- The next material blocker is independent evidence for missing-event
  neutrality plus lifecycle and terminal outcomes, using ADR 0221's bounded
  sample.

## Rejected alternatives

### Feed the 2026-09-04 sparse ledger directly into every historical path

Rejected because its later fixed basis and outcome-reconciliation authority do
not satisfy a point-in-time feature contract.

### Interpret an omitted ledger row as factor one

Rejected because the current source snapshot does not prove complete event
absence or revision history.

### Adjust the price-return label for cash dividends

Rejected because that changes the declared estimand to total return and still
does not model an option return.

### Apply a `t+1` split again after entering at the `t+1` open

Rejected because the entry price is already on the effective session's basis.

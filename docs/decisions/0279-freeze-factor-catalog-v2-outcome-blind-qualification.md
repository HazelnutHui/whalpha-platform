# ADR 0279: Freeze Factor Catalog V2 Outcome-Blind Qualification

## Status

Accepted

## Date

2026-09-15

## Context

ADR 0278 registered eight Factor Catalog V2 definitions before real values or
forward outcomes were inspected. Formula correctness alone does not prove that
the governed historical panel can calculate those definitions with adequate
coverage, time balance, variation, or non-redundancy. Those properties must be
tested before registering any new outcome trial.

V2 uses a 127-session input window. Treating one stock-specific EOD or split
defect as a complete cross-section failure would discard otherwise valid peers
and make long-window qualification misleading. Benchmark failure is different:
every relative definition depends on the same SPY path.

## Decision

Freeze protocol `quant-research-factor-qualification/2.0.0`, logical
fingerprint
`b74214155cc148d1e0d37c530ab4fea2f385af1a81237b901eec45e1fee2eb0b`.
It is bound to Factor Catalog V2 fingerprint
`6620000334a0a8bd23103341dfc1958d57c712a063dff0a39e23ffc82d51bed5`
and cumulative discovery ledger fingerprint
`502834abe5bfc171f80206138b36c8bf973c9fcc84078592b8dc92ccd5bee368`.

The report must cover the exact 287-session, 437,402-path reconstructed
Membership population. Membership is used only at each signal session and is
not projected backward through the warm-up window. A stock-specific EOD or
split-evidence defect quarantines only that stable `instrument_id`; a SPY
defect closes the complete signal session.

For each definition, the protocol measures availability, missing reasons,
eligible sessions in both chronological halves, distinct values, same-session
ties, distribution tails, and session/instrument concentration. Qualification
requires at least 90% cell availability, 250 eligible sessions with at least
100 instruments, at least 120 eligible sessions in each chronological half,
100 distinct values, and no more than 95% same-session tie excess.

All 28 factor pairs receive same-session Spearman diagnostics. A pair is a
near-duplicate only with at least 60 eligible sessions, absolute correlation
of at least 0.90 in at least 80% of them, and a dominant sign in at least 90%
of non-zero sessions. Within a registered related-factor group, the lower
fixed redundancy priority is retained. A cross-group near-duplicate pauses the
next outcome protocol for outcome-blind adjudication; it is not silently
selected using realized results.

The Dell implementation uses vectorized NumPy calculations for bounded local
runtime and retains the pure Decimal calculator as an independent reference.
One owner-only report and one exact full replay are required. Neither run may
accept forward outcomes, performance metrics, network access, or writes to
canonical `/data`.

This decision is independent of the closed Strong-Leader Pullback strategy.
Its legacy development census is reused only as immutable source evidence;
the V2 population is freshly fingerprinted from signal-date Membership rows
and the chronological plan is derived directly from the frozen sessions.

## Consequences

- Real V2 values may be inspected only through this outcome-free report.
- At least two non-redundant candidate-Alpha definitions must qualify before a
  Development screening protocol can be considered.
- Qualification does not admit a factor, construct a model, express a
  strategy, or authorize Validation, Holdout, Candidates, publication, or
  trading.
- A failure closes or repairs the implementation/data boundary; it cannot be
  converted into an Alpha claim by changing thresholds after inspection.

## Alternatives considered

### Reuse the V1 complete-cross-section rule

Rejected because a 127-session window would turn unrelated stock-specific
gaps into broad session loss.

### Inspect factor returns while diagnosing coverage

Rejected because coverage thresholds and redundancy resolution would then be
outcome-guided.

### Choose the more attractive correlated definition after seeing values

Rejected. Related groups carry fixed priorities before the report is run.

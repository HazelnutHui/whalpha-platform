# ADR 0271: Freeze Reconstructed Development Statistics Before Reading Results

- Status: Accepted
- Date: 2026-09-15

## Context

The immutable reconstructed development dataset now contains real 1/3/5-session
labels, including exact observations, finite terminal intervals, unavailable
evidence, and securities that could not be entered at the registered next open.
No aggregate return, parameter comparison, or winner has yet been inspected.

The earlier fixture statistics freeze session-balanced inference and the
24-combination selection objective, but they cannot represent interval
endpoints, separate missing-entry states from source gaps, or retain excursions
whose future path is incomplete. Those decisions must be fixed before real
outcomes can influence the implementation.

## Decision

Add
`strong-leader-pullback-reconstructed-development-statistics-policy/1.0.0`
without changing the registered method or 24-combination budget. Policy
fingerprint:
`a420675be6c7eb580bc95906f4ef0588eccee0d9640047a57d459423e5708f37`.

1. Evaluate all 24 combinations at the 1-, 3-, and 5-session horizons. Three
   deterministic interval scenarios are mandatory: every lower endpoint, every
   upper endpoint, and the contrast-adverse assignment of signal lower/control
   upper. No midpoint or expected-value imputation is allowed.
2. Preserve the registered equal-weight within-session signal-minus-control
   contrast, five-session circular moving-block bootstrap, 2,000 replicates,
   percentile 90% interval, and one-sided centered-null probability. An
   independent Oracle must reproduce every inferential value.
3. Preserve the registered development selection objective: maximize the
   three-session contrast lower bound, then mean contrast, numeric signal count,
   and stable combination ID. Development does not apply Holm; the full
   24-member Holm family remains a validation control.
4. A parameter may lock only when all three endpoint scenarios select the same
   combination, every scenario meets the registered signal/control/comparable-
   session and observed-Regime floors, and no `unavailable_evidence` row occurs
   in any primary-horizon signal or control cohort across the selection family.
   Endpoint instability, insufficient evidence, or an unavailable source fact
   yields no lock.
5. `unexecutable_no_next_open` is not assigned a return. It remains in the
   denominator and is reported separately as a no-trade execution outcome; it
   is neither a zero return nor evidence that a security became worthless.
6. Exact, terminal-exact, terminal-interval, unavailable, and unexecutable
   counts remain separate by signal and control. MFE/MAE use only complete
   observed intraperiod paths and disclose their smaller denominator.
7. Report event-study expectancy, median, SPY-relative median, win rate, average
   win/loss, payoff ratio, Profit Factor, MFE/MAE, session concentration,
   chronological halves, Regime slices, and 0/10/25/50 basis-point-per-side
   sensitivities. AR, Sharpe, MDD, Alpha, Beta, and option returns remain
   prohibited because no portfolio or option construction exists.
8. The result remains private, reconstructed latest-vintage development
   evidence. A lock does not open validation. A separate formal review must
   confirm identities, reproduction, selection invariance, limitations, and
   custody before validation can be authorized.

## Consequences

The first real comparison can now fail cleanly because of missing evidence,
weak sample support, or interval-sensitive selection. It cannot hide a terminal
interval inside one point, silently omit an unavailable path, or turn an
in-sample winner into a public performance claim. Validation, holdout,
Candidate activation, publication, deployment, and Production remain closed.

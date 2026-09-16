# Campaign Three Development Screening Audit — 2026-09-16

## Verdict

Campaign Three is closed at `closed_no_candidate_alpha`. The one formal screen
and one exact replay are byte-identical. All three registered trials are
`rejected_screen`; no Alpha, risk guard, model input, or downstream authority
is selected.

## Frozen execution

- implementation revision:
  `91eb383a70eb209ec9f998954586b3499ca1d4b8`;
- formal and replay report SHA-256:
  `8ba525beb7e39e7e9175fd0359b45e17c44c16cd6c1a083fb53c99704c4f13e1`;
- report logical fingerprint:
  `7b4f0e60c7dd3aa4faa01d16e303ed7bec35a4af5a7b992a4941ef01e3a439f9`;
- 106 signal sessions from 2025-07-22 through 2026-01-07;
- 167,860 aligned observations and 503,580 labels; and
- zero network requests, canonical-data writes, or Production writes.

Label states reconcile to 503,241 observed exact, 92 terminal exact, 46
terminal interval, 129 unavailable, and 72 unexecutable rows.

## Decisions

| Registered question | Role | Primary interaction evidence | Frozen decision |
| --- | --- | --- | --- |
| Breakout position by market breadth | Candidate Alpha | worst primary beta -0.0029; second-half beta about -0.065; worst registered lower bound -0.0654; Holm-adjusted p 1.0000 | rejected |
| Dollar-volume surprise by market participation | Candidate Alpha | worst primary beta -0.0143; second-half beta about -0.056; worst registered lower bound -0.0466; Holm-adjusted p 1.0000 | rejected |
| Safer residual volatility by broad realized volatility | Risk guard | primary beta +0.0567, but second-half beta -0.1258; worst registered lower bound -0.6671; Holm-adjusted p 0.4150 | rejected |

The Alpha interactions fail direction, second-half stability, both registered
bootstrap lower-bound gates, and Holm control. Breakout breadth also has
negative favorable-state mean rank IC. The risk guard's positive pooled slope
does not survive the original chronological halves or either registered block
world.

## Closure

Ledger V5 records all three outcomes and preserves the cumulative count of 17
formal trials under logical fingerprint
`424da475ee8aa87a7b54eac8c9eec64f32035d7ae1a7d491b90604863edc5df1`.
Validation, Holdout, Model Construction, Strategy Expression, Candidate
activation, publication, broker access, and trading remain closed. The next
research action is a new outcome-blind intake, not post-outcome repair of this
campaign.

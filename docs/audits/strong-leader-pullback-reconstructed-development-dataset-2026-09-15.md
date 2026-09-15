# Strong-Leader Pullback Reconstructed Development Dataset Audit — 2026-09-15

## Decision

The first immutable reconstructed development dataset passed construction and
an independent full reread on Dell. It is admitted only for the registered
development comparison. It does not open validation, holdout, a performance
claim, Stock Candidates, publication, deployment, or Production.

## Retained package

- custody:
  `historical-evidence/strong-leader-pullback-reconstructed-development-dataset/dataset=20260915-v1`
- implementation revision:
  `386b51640e7918173509bbcb419d8f979b90227b`
- created at: `2026-09-15T05:51:31Z`
- manifest SHA-256:
  `92e9f078db840d3d8e341b4e15757429e26ff4acbdb9564aebb387aa07a5a267`
- logical fingerprint:
  `91300da44caf35f838912db3d4060a6bbc98aeea23f81845194e1302e11c43c4`

The package binds the admitted V2 population, registered method, complete
outcome-blind diagnostic, chronological plan, EOD sessions, split evidence,
and terminal-reference ledger. The independent replay returned
`already_present` with the same identities and counts.

## Population and label states

| Measure | Verified value |
| --- | ---: |
| Development signal sessions | 105 |
| First / last signal session | 2025-07-23 / 2026-01-07 |
| Complete observations | 166,313 |
| Label rows | 498,939 |
| 1 / 3 / 5-session labels | 166,313 each |
| `observed_eod_exact` | 498,580 |
| `terminal_reference_exact` | 90 |
| `terminal_reference_interval` | 44 |
| `unavailable_evidence` | 153 |
| `unexecutable_no_next_open` | 72 |
| Validation / holdout labels | 0 / 0 |

The terminal ledger contains 65 entries: 48 exact and 17 finite interval.
Every observation has exactly three label rows. Exact, interval-censored,
unavailable, and unexecutable states remain distinct.

## Files and custody

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `observations.parquet` | 13,836,411 | `1961ad871132abc722f838a7151beef11e574a75ff7c0f65da37e6a1e432cc5b` |
| `labels.parquet` | 59,081,464 | `b0f93f7c3908bf3e4ab637ac43b1d6a3773a20a449bb90735ecacc532ed24b69` |
| `manifest.json` | 38,660 | `92e9f078db840d3d8e341b4e15757429e26ff4acbdb9564aebb387aa07a5a267` |

The custody parent and dataset directory are owner-only `0700`; retained files
are immutable `0400`. The accepted package contains no symlink or staging
residue and wrote no network, canonical `/data`, Candidate, publication,
deployment, or Production state.

## Defects found before retention

Three real-source conditions failed closed before any package was written:

1. A non-`CLEAR` split-adjustment row was correctly classified but was still
   passed to the numeric adjuster. The control flow now retains the label as
   `unavailable_evidence` with null outcomes.
2. Some split-adjusted prices required more than ten decimal places. Stored
   prices and returns could therefore disagree at the contract boundary. The
   implementation now freezes price precision first and calculates every return
   from those retained prices.
3. One MT observation lacked the next-session EOD row but traded again on the
   following session. Absence was not terminal evidence. It is now retained as
   `unavailable_evidence`; neither a delayed entry nor a false terminal event is
   inferred.

Each correction has a regression test. Failed attempts left no accepted output
or staging residue.

## Interpretation and next gate

The labels are reconstructed, latest-vintage underlying-stock price outcomes.
They are not as-operated history, total returns, alpha, option returns, trading
recommendations, or Production signals. Raw labels contain no transaction
costs; the preregistered 0/10/25/50 basis-point-per-side scenarios belong to the
derived evaluation layer.

Before any return summary is inspected, the development-statistics and
specification-lock protocol must be frozen in code and documentation. It must
evaluate all 24 registered specifications, preserve adverse interval endpoints,
count unavailable and unexecutable rows, apply session-balanced inference and
the registered controls, and lock at most one specification without opening
validation or holdout.

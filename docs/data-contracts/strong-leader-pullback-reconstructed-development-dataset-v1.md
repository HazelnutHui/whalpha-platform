# Strong-Leader Pullback Reconstructed Development Dataset V1

## Purpose

`strong-leader-pullback-reconstructed-development-dataset/1.0` is the first
real, owner-only development dataset for the preregistered Strong-Leader
Pullback study. It binds outcome-free observations to independent 1/3/5-session
underlying-stock labels without opening validation or holdout.

## Observation scope

The observation table contains every member of each complete, usable
development cross-section. Rows retain the canonical method and feature
fingerprints, stable `instrument_id`, signal session, ticker locator, Regime,
the six registered feature values, and the original observation fingerprint.
The complete population must reproduce the retained method diagnostic before
the development subset is written.

## Label states

Each observation has exactly three label rows:

- `observed_eod_exact`: next-open entry and horizon-close exit are both
  observed after frozen split adjustment;
- `terminal_reference_exact`: entry is executable and the missing horizon exit
  has one exact retained terminal reference;
- `terminal_reference_interval`: entry is executable and the missing horizon
  exit remains a finite lower/upper interval; or
- `unexecutable_no_next_open`: the security has no next-session opening trade,
  so every numeric outcome remains null; or
- `unavailable_evidence`: a path intersects unresolved adjustment or source
  integrity evidence, so no numeric outcome is admitted.

Exact labels repeat the same lower and upper value. Interval labels preserve
both endpoints and cannot be point-imputed. MFE/MAE require every expected path
bar; terminal-reference and incomplete intraperiod paths leave excursions null
with an explicit reason.

## Isolation and authority

The package is immutable, owner-only, and self-fingerprinted. Its manifest
binds the V2 admission, method diagnostic, chronological plan, split evidence,
terminal evidence, source EOD sessions, observation table, and label table.

The package asserts:

- reconstructed latest-vintage research, not `as_operated` history;
- development only;
- zero validation labels and zero holdout labels;
- raw underlying-stock price outcomes with no transaction costs;
- zero parameter selection and zero performance claims; and
- zero network, canonical, Candidate, publication, deployment, and Production
  writes.

# Strong-Leader Pullback Method V1

## Purpose

`strong-leader-pullback-method/1.0` is the single outcome-blind method source
for the first WH Alpha research program. It prevents the input calculator,
Quant Research Lab, and later research reports from maintaining independent
copies of the formula, parameter grid, or evaluation design.

This contract does not run a backtest and does not authorize real labels,
parameter selection, validation, holdout access, performance claims, Stock
Candidate activation, publication, or deployment.

## Immutable bindings

- method ID: `whalpha.strong-leader-pullback`;
- method version: `strong-leader-pullback-method/1.0.0`;
- frozen research version: `strong-stock-pullback-research/1.0`;
- parameter combinations: 24;
- input calculation: `strong-leader-pullback-input-features/1.0.0`;
- input feature fingerprint:
  `407d9e1b77b4b60976583f1254fca8a46e94718d84c9d430b094e5a7a025e76d`;
- method-engineering launch fingerprint:
  `1abb4ed53d4a4cb5bb6482432db254a0019168aae2712983a9d00aaa4cffef8c`;
- method logical fingerprint:
  `ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba`.

The method fingerprint covers method identity, experiment and policy
bindings, formulae, data lineage, parameter values, evaluation design,
decision gates, counterevidence, invalidation, and every authorization flag.
Changing any of those facts requires a new fingerprint and, when semantics
change, a new version rather than silent mutation.

## Method contents

The contract discloses:

- the decision use, hypothesis, mechanism, Primary and sensitivity Universes,
  completed-close cutoff, next-open entry basis, and 1/3/5-session horizons;
- the eight registered feature requirements and their exact calculation
  semantics, clocks, lookbacks, transforms, units, expected direction, and
  missingness handling;
- the two leadership gates, three ATR-depth bands, two recovery branches, and
  two volume caps, with development-only selection scope;
- chronological 50/25/25 development, validation, and sealed-holdout design;
- five-session purge and embargo, the leader non-signal control, SPY
  benchmark, session-balanced block bootstrap, multiplicity correction,
  fixed cost scenarios, and single-use holdout rule; and
- advancement gates, weaknesses, required counterevidence, and invalidation
  conditions.

`requirement_source_family` preserves the semantic source named by the frozen
experiment. `raw_source_families` separately names the actual inputs used to
calculate that feature. For price-derived features this includes both EOD
bars and the split-adjustment ledger. Neither field may be substituted for the
other.

## Fail-closed invariants

- Every method feature and parameter must reconcile with the frozen
  preregistration in stable order.
- The registered 24-combination search budget cannot expand through the Lab
  projection or input calculator.
- Input-feature identity remains shared with the outcome-free batch contract.
- Real outcome fields are absent.
- Parameter selection, formal development, validation, holdout access,
  performance claims, and Candidate activation are all fixed to `false`.
- The formal data gate remains `rejected_data_blocked` even though
  outcome-blind method engineering is permitted.

The checked-in Lab JSON is a derived projection of this contract. Automated
tests require its formulae, displayed parameter values, method fingerprint,
feature fingerprint, and experiment fingerprint to match the canonical
builder exactly.

The pure mechanics service also consumes this contract directly. It parses the
registered canonical parameter strings into numeric execution rules, emits all
24 combinations, applies inclusive boundaries, and stamps the method version
and fingerprint on every mechanics batch. It emits cohort assignments only;
real outcomes remain outside the authorized method-engineering path.

# Quant Research Lab Model Record V1

## Purpose

The Quant Research Lab contracts separate a disclosed research method from a
research result and from Product activation. They allow a model to be fully
audited without implying that it works or that Stock Candidates may use it.

The three contract versions are:

- `quant-research-lab-model-record/1.2`;
- `quant-research-lab-result/1.0`; and
- `quant-research-lab-catalog/1.0`.

All models are immutable, reject extra fields, and carry deterministic logical
fingerprints.

## Model record

A model record binds:

- stable model identity, owner, personal-research disclosure, version, date,
  lifecycle, evidence scope, and current-market applicability;
- decision use, hypothesis, economic rationale, Universe, signal cutoff,
  modeled entry, horizon, signal logic, and ranking boundary;
- every feature's frozen requirement family, actual raw-source families and
  fields, availability cutoff, lookback, exact formula, transform, unit,
  expected direction, and missingness rule;
- all parameter candidates, selection scope, rationale, and registered search
  budget;
- chronology, warm-up, purge, embargo, labels, benchmark, control, inference,
  multiplicity, cost scenarios, holdout custody, and whether a portfolio has
  been defined;
- optional outcome-blind method-engineering evidence with its report/code
  bindings, interval, declared and computable paths, explicit exclusions,
  proxy bases, observed/unobserved Regimes, and limitations;
- advancement gates, strength, weakness, required counterevidence,
  invalidation, blockers, and risk disclosures; and
- canonical method, experiment, feature, evaluation, implementation, result,
  and record reproduction bindings.

An `active` model requires a separate 64-character Candidate activation
fingerprint. Every other lifecycle state must remain Candidate-ineligible.
Validated, shadow, and active lifecycle states require a real signal/event or
portfolio result; fixture evidence cannot advance them.

`preregistered_data_blocked` requires explicit blockers. A method-only record
cannot claim a validation date, out-of-sample observations, or a result
publication.

Method-engineering evidence does not change that rule. Its path coverage is a
computability measure, never a hit rate, return, performance metric, or reason
to select a parameter. The disclosure fixes forward outcomes, performance
metrics, parameter selection, and Candidate authority to false.

## Result publication

| Evidence scope | Permitted content | Prohibited interpretation |
| --- | --- | --- |
| `method_only` | Method and limitations only | No period, observations, metrics, or performance |
| `fixture_only` | Mechanic-test values clearly marked fixture-only | No real performance or Candidate authority |
| `signal_event_study` | Event outcomes, controls, costs, uncertainty, and stability | No portfolio AR, Sharpe, MDD, or other portfolio-only metric |
| `portfolio_simulation` | Event and portfolio metrics | No portfolio metric without frozen construction fingerprint |

Real signal or portfolio results require a valid period, source-dataset
fingerprint, non-empty metric ledger, and explicit research-performance
authority. Each metric binds its split, sample count, cost status, unit,
benchmark where relevant, and paired uncertainty bounds. Duplicate
metric/split/horizon/slice keys, non-finite values, and reversed intervals are
invalid. Every real result also retains counterevidence and limitations.

A result publication always fixes `candidate_authority_granted=false`.
Statistical evidence does not itself approve operational use.

## Catalog and Candidate boundary

The catalog lists model records and one featured record. It may name at most
three active Candidate models. Every named model must exist in the catalog, be
in `active` lifecycle state, be marked Candidate-eligible, and bind a separate
activation fingerprint.

The initial catalog names no active Candidate model.

## First registered projection

The checked-in browser record is the canonical method projection for:

- model: `whalpha.strong-leader-pullback`;
- method version: `strong-leader-pullback-method/1.0.0`;
- method fingerprint:
  `ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba`;
- lifecycle: `preregistered_data_blocked`;
- evidence: `method_only`;
- model-record fingerprint:
  `ec6f8473d1824526bcdecffbc8044e82201e325e4f2036253378773f13443831`;
- catalog fingerprint:
  `10e22b6dac375df7bea2f3b48130604060fa9aa512654e8838480f08d620adb8`;
- method-engineering evidence: independently replayed reconstructed proxy,
  417,209 of 437,402 declared paths computable across 287 sessions;
- real result publication: none; and
- active Candidate models: none.

The web application reads the same JSON record that the Python contract test
validates against the canonical builder. The record contains no provider
request, `/data` mutation, real evaluation, Candidate change, Snapshot change,
or deployment authority.

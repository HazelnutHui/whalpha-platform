# Quant Research Lab Model Record V1

## Purpose

The Quant Research Lab contracts separate a disclosed research method from a
research result and from Product activation. They allow a model to be fully
audited without implying that it works or that Stock Candidates may use it.

The three contract versions are:

- `quant-research-lab-model-record/1.0`;
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
- every feature's source family and fields, availability cutoff, lookback,
  exact formula, transform, unit, expected direction, and missingness rule;
- all parameter candidates, selection scope, rationale, and registered search
  budget;
- chronology, warm-up, purge, embargo, labels, benchmark, control, inference,
  multiplicity, cost scenarios, holdout custody, and whether a portfolio has
  been defined;
- advancement gates, strength, weakness, required counterevidence,
  invalidation, blockers, and risk disclosures; and
- experiment, feature, evaluation, implementation, result, and record
  reproduction bindings.

An `active` model requires a separate 64-character Candidate activation
fingerprint. Every other lifecycle state must remain Candidate-ineligible.
Validated, shadow, and active lifecycle states require a real signal/event or
portfolio result; fixture evidence cannot advance them.

`preregistered_data_blocked` requires explicit blockers. A method-only record
cannot claim a validation date, out-of-sample observations, or a result
publication.

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
- research version: `strong-stock-pullback-research/1.0`;
- lifecycle: `preregistered_data_blocked`;
- evidence: `method_only`;
- model-record fingerprint:
  `ed7fb37c35c8b97ba5a25114d407212dbeddb7fc7f876786b672668214b620d7`;
- catalog fingerprint:
  `0737ba4cefe58bcfbe00004e79bb956454cea3db426fe0040037fc06b9a63826`;
- real result publication: none; and
- active Candidate models: none.

The web application reads the same JSON record that the Python contract test
validates against the canonical builder. The record contains no provider
request, `/data` mutation, real evaluation, Candidate change, Snapshot change,
or deployment authority.

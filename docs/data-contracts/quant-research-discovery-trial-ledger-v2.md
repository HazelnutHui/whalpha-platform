# Quant Research Discovery Trial Ledger V2

## Purpose

`quant-research-discovery-trial-ledger/2.0` is the append-only preregistration
state before Factor Catalog V2 opens Development outcomes. The immutable ledger
version is `whalpha.quant-research.discovery-trial-ledger/2.0.0`; logical
fingerprint:
`cdc07a2194540b94dbba6bfee673a720ce232dc1d939f8b2c7496dda628946e9`.

## Frozen content

- carries the completed V1 campaign and all eight consumed trials unchanged;
- appends four V2 candidate-Alpha and two V2 risk-guard trials;
- records 14 cumulative formal trials: nine Alpha and five risk-guard trials;
- records zero outcome-tested conditioner interactions and zero
  applicability-input outcome trials;
- retains one V1 risk guard and zero admitted Alpha factors;
- marks every V2 trial `registered_pending_development_screen`, with no outcome
  access date, result report, model-input permission, or Candidate permission;
- discloses that V2 is adaptive to consumed Development evidence.

## Mutation rule

Neither the consumed V1 campaign nor the registered V2 trial list may be
removed, reordered, relabeled, or overwritten. Execution produces a new ledger
version that closes each V2 trial with the immutable result identity and keeps
all failures. A later campaign must append again rather than edit this version.

The ledger grants only the finite V2 Development-screen execution described in
ADR 0281. Validation, Holdout, Model Construction, Strategy Expression,
Candidate activation, publication, broker, and order authority remain closed.

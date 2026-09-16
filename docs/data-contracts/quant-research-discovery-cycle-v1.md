# Quant Research Discovery Cycle V1

## Purpose

`quant-research-discovery-cycle/1.0` defines an indefinitely renewable Factor
Discovery program made from finite, independently closed campaigns. Version:
`whalpha.factor-discovery-cycle/1.0.0`; logical fingerprint:
`55c1eaccbd5ef5c8ef6dd695c4e4e010ed0e11c6483e55f1a2ce6b70898f8218`.

The program has no fixed campaign limit. This does not create an unlimited
outcome search: every campaign has its own finite trial budget, stopping rule,
result, replay, and append-only ledger close.

## Fixed cycle

1. hypothesis intake;
2. deduplication;
3. point-in-time data admission;
4. outcome-blind factor qualification;
5. outcome protocol preregistration;
6. one finite Development screen;
7. exact replay and adversarial review; and
8. ledger close, authority decision, and return to hypothesis intake.

Only stages 6 and 7 may read the registered Development outcomes. Validation
and Holdout remain separate and closed unless a complete factor-model-strategy
lineage later earns their own authority.

## Duplicate identity

Novelty is assessed jointly across:

- economic mechanism;
- information set and cutoff;
- formula and transformation;
- Universe and eligibility;
- horizon and label;
- parameter neighborhood; and
- related-hypothesis family.

Exact duplicates are rejected. Near-duplicates are grouped so their variants
share a related family and multiplicity accounting. Economically distinct
questions may proceed only as new registered trials. A failed campaign cannot
be reopened under changed labels or gates.

## Finite campaign budget

Before outcomes, each campaign freezes factor/interaction count, parameter
variants, outcome horizons, related families, multiplicity method, selection
cap, and stopping rule. Lineage mismatch, stage leakage, trial-budget breach,
replay failure, or sealed-partition breach pauses the affected campaign without
deleting previous evidence.

The contract's embedded state is the immutable baseline at version 1.0
registration: `ready_for_next_campaign_design`, two closed campaigns, and 14
formal trials. It is not a live current-state record. Campaign Three was later
registered in Ledger V4 with three unread trials, bringing cumulative formal
trials to 17; read [current status](../project/current-status.md) and the latest
ledger contract for current state. No model input is authorized.

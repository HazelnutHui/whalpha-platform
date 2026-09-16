# Quant Research Multi-Agent Governance V1

## Purpose

`quant-research-multi-agent-governance/1.0` turns ADR 0194 into an executable
role, access, and handoff contract for the Campaign Three pilot. It coordinates
research work; it does not create Alpha or grant access to outcomes.

## Roles

| Role | Primary responsibility | Maximum data access | Required handoff |
| --- | --- | --- | --- |
| Research controller | stage and budget reconciliation | compact summaries and registered Development result | stage decision |
| Data evidence | lineage, timing, coverage, missingness | outcome-blind source and derived data | data-admission report |
| Hypothesis | economic and falsifiable idea definition | outcome-blind summaries | hypothesis cards |
| Implementation | deterministic formula and tests | outcome-blind feature inputs | implementation manifest |
| Evaluation | frozen Development screen | registered Development slice only | immutable evaluation report |
| Red team | outcome-blind leakage, chronology, threshold, and implementation attacks | outcome-blind source and derived data | outcome-blind red-team report |
| Approval/publication | evidence reconciliation and milestone wording | reviewed reports, not sealed row access | promotion/publication decision |

The controller cannot manufacture a missing handoff. No agent can grant itself
new data, stage, publication, deployment, broker, or trading authority.

## Ordered and parallel work

Outcome-blind evidence review, hypothesis drafting, implementation review, and
documentation may be parallel when they do not write the same artifact.
Development outcome access is not part of the current pilot. A later contract
version may activate evaluation and result-red-team roles only after the unique
protocol-freeze handoff. Evaluation must then finish before role-distinct
replay/red-team review; ledger close follows both. Validation and Holdout are
never part of this pilot.

## Shared accounting

All roles use one campaign identity, seven-field duplicate signature, finite
trial budget, content-addressed input registry, and append-only cumulative
ledger. Agent count does not increase the selection cap or reset multiplicity.
Exact and near duplicates are rejected or grouped before outcome access.

## Pilot state

The governance contract is ready for the third-campaign pilot. Campaign Three
itself remains unregistered. The market-state input is still undergoing
outcome-blind qualification; zero new outcome trials have been opened.

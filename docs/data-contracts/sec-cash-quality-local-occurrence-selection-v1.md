# SEC Cash-Quality Local Occurrence Selection V1

## Purpose

`quant-research-sec-cash-quality-occurrence-selection/1.0` records an
outcome-blind, issuer-level decision for the three ADR 0300 queries at one
explicit fiscal endpoint. It consumes caller-supplied rows already read from
the retained normalized Company Facts custody; the service itself has no I/O.

## Required binding

Every result binds:

- the exact ADR 0300 query-registry fingerprint;
- normalized-source manifest and content fingerprints; and
- the normalized source's filing-clock manifest fingerprint.

The request fixes CIK, fiscal year, fiscal-year origin, fiscal period, period
end, evaluated XNYS session, and UTC cutoff.

## Selection rules

- Admit only exact `us-gaap` concepts, USD, registered forms and fiscal
  periods, numeric values, admitted normalization, and admitted filing clocks.
- Require source availability and eligible session no later than the request.
- Require Assets to be instant with a null start.
- Require every duration to start at the request's bound fiscal-year origin.
  Q2/Q3 additionally require a clean same-concept Q1 occurrence that witnesses
  that same origin.
- Collapse identical duplicate rows only within one accession.
- Select the latest clean accession visible at the cutoff.
- Quarantine within-accession conflicts, ambiguous origin witnesses, or tied
  latest accessions.
- Require selected CFO and net income for the endpoint to share one accession.

Each query returns `selected`, `not_available`, or `quarantined`. Joint
readiness is `ready_for_endpoint_occurrence_use_only` only when all three are
selected and the duration-pair accession is coherent; otherwise it is
`blocked` with typed reasons.

## Boundary

The contract authorizes no network access, security projection, applicability
adjudication, TTM derivation, factor materialization, outcomes, Validation,
Holdout, trial, Candidate use, canonical write, or Production write. A ready
endpoint is not evidence that four consecutive quarters or both Assets
boundaries exist.

See [ADR 0301](../decisions/0301-select-local-sec-cash-quality-occurrences-before-ttm.md).

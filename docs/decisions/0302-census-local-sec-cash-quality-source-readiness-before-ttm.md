# ADR 0302: Census Local SEC Cash-Quality Source Readiness Before TTM

## Status

Accepted

## Date

2026-09-17

## Context

ADR 0299 freezes the cash-earnings-quality source plan, ADR 0300 registers its
three exact SEC queries, and ADR 0301 defines issuer-level occurrence selection
at one explicit fiscal endpoint. None establishes whether the retained local
Company Facts custody contains usable Assets, net-income, and operating-cash-
flow occurrences at observed endpoints.

A source-readiness census must remain outcome-blind and precede TTM
construction. It cannot use a security population because point-in-time
identity and nonfinancial applicability remain unresolved. It also cannot
create an unbounded issuer-by-date panel or retain selected financial values.

## Decision

Adopt `quant-research-sec-cash-quality-source-readiness-census/1.0` as a
bounded, local-only aggregate census.

The plan binds the normalized Company Facts manifest/content, filing-clock
manifest, occurrence schema, exact occurrence-artifact identities, ADR 0300
registry, source range, knowledge cutoff, and single-process budgets. The first
plan permits exactly the bound source denominator, at most 2,000,000 target
occurrences, 1,000,000 observed endpoints, and 300,000 retained target rows per
source worker. Any excess or binding drift stops without a partial result.

The runner formally rereads the normalized package, streams every bound
occurrence artifact in 65,536-row batches, and retains only the three target
concepts in worker-bounded memory. It records sequential occurrence rejection
reasons, then evaluates the union of observed target-concept CIK/fiscal-year/
fiscal-period/end-date keys under ADR 0301 semantics. It does not invent endpoints for
issuers or periods absent from all three concepts.

Fiscal-origin evidence must be unique across the two duration concepts. A
missing or ambiguous joint origin blocks the endpoint. Otherwise the census
records per-query selected/not-available/quarantined counts, CFO/net-income
accession coherence, and aggregate reason counts. No selected value, CIK,
accession, or occurrence identifier enters the result.

Independent verification reruns the complete census with reverse artifact,
worker, CIK, and endpoint traversal and requires byte-identical canonical
results.

The census authorizes no network request, security projection, applicability
adjudication, TTM derivation, factor materialization, outcome, Validation,
Holdout, trial, Candidate, canonical write, or Production use.

## Consequences

The result measures only positive-evidence issuer endpoints observed in the
local custody. It is not issuer-population coverage, security coverage, a
four-quarter chain, or source qualification. Missing identity/applicability,
unobserved issuer endpoints, consecutive-quarter requirements, opening Assets,
and all TTM and replay gates remain downstream blockers.

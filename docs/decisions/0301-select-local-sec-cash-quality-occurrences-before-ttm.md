# ADR 0301: Select Local SEC Cash-Quality Occurrences Before TTM

## Status

Accepted

## Date

2026-09-17

## Context

ADR 0299 freezes a plan-only SEC cash-earnings-quality path. ADR 0300
registers three exact issuer-level queries but authorizes no query execution or
occurrence selection. The retained normalized Company Facts custody already
contains concept, unit, start/end dates, fiscal year/period, form, accession,
value, filing date, conservative availability, and eligible-session fields.
Its formal reader verifies the bound filing-clock and every Parquet artifact.

The older point-in-time selector is bound to the immutable first fundamental
registry and its annual-flow type. Reusing it for Q2/Q3 cash-quality durations
would not prove that a duration is cumulative from the fiscal-year origin.

Security identity and nonfinancial applicability remain unresolved for the
cash-quality path. They prevent security projection and coverage, but do not
prevent a strictly issuer-level occurrence-readiness decision.

## Decision

Add an independent pure selector and typed readiness result for one explicit
CIK, fiscal year, fiscal-year origin, fiscal period, period end, evaluated
session, and cutoff.
The caller must bind a formally read normalized-source manifest/content
fingerprint, its filing-clock manifest fingerprint, and the ADR 0300 query
registry fingerprint.

Selection admits only exact namespace, concept, USD unit, form, fiscal period,
period shape, numeric value, normalization, filing-clock, availability, and
cutoff matches. It groups duplicates within one accession and selects the
latest clean accession available at the cutoff. Conflicts or tied latest
accessions quarantine instead of using row order.

For Q2 and Q3 duration queries, an admitted same-concept Q1 occurrence in the
same fiscal year must witness the request's fiscal-year origin. Only target
durations with that start date qualify. Q1 and FY durations must also begin at
the explicitly bound origin. Assets require an instant occurrence with a null
start. CFO and net income at the requested endpoint must select the same clean
accession.

The result can be `ready_for_endpoint_occurrence_use_only` or `blocked`. It is
not TTM readiness. It authorizes no network request, security projection,
applicability adjudication, TTM derivation, factor materialization, outcome,
Validation, Holdout, trial, Candidate, canonical write, or Production use.

## Consequences

The registered queries now have a deterministic, network-free occurrence
selection primitive compatible with retained custody. Missing Q1 origin
witnesses, ambiguous starts, incoherent CFO/NI accessions, unavailable facts,
and value conflicts remain explicit blocks.

No local full-custody scan is performed by accepting this ADR. A later bounded
readiness census may stream the existing Parquet custody into the pure selector
only after separately fixing its finite issuer/endpoint population and report
custody. Identity, applicability, TTM construction, coverage, and replay remain
later gates.

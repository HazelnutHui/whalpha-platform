# ADR 0304: Derive Issuer-Level SEC Cash-Quality TTM Feasibility

## Status

Accepted

## Date

2026-09-18

## Context

ADR 0303 retained exact values and lineage for 82,440 ready issuer endpoints.
It did not prove four-quarter chains or opening and closing Assets. The next
stage must use only that 58.9 MB custody and must not reread the 41.6-million-
occurrence normalized source.

## Decision

Adopt `quant-research-sec-cash-quality-ttm-coverage/1.0` as a bounded issuer-
level derivation and aggregate coverage contract.

Q1 is its reported duration. Q2, Q3, and FY discrete flows are respectively
YTD less Q1, YTD less Q2, and FY less Q3 within one fiscal year and origin.
Negative and zero CFO or net-income values remain valid arithmetic inputs.
Every endpoint retains its selected amendment clock, accession, and occurrence
lineage; CFO and net income remain accession-coherent at each endpoint.

A TTM endpoint requires four consecutive discrete quarters plus the preceding
endpoint's Assets as the opening boundary. The economic fiscal-cycle key is
CIK plus the duration origin, not Company Facts `fy`: comparative facts in a
later filing can carry that filing's fiscal focus. Within-origin period order
must be Q1, Q2, Q3, FY. Across cycles, the next Q1 fiscal origin must be exactly
one day after the prior FY end. Annual durations from 350 through 378 inclusive are
accepted, which includes 52- and 53-week years without treating labels as
fixed calendar quarters. Stubs, gaps, ambiguous fiscal-period endpoints,
missing predecessors, and zero average Assets fail closed. Negative average
Assets remain visible rather than silently rewritten.

The result reports only issuer-level feasibility and typed blockers. Forward
and reverse issuer traversal must produce byte-identical sorted rows and the
same result. Owner-only atomic custody retains the plan, derived rows, result,
and replay verification with exact reread.

No listed-security projection, applicability adjudication, factor
materialization, outcome, Validation, Holdout, trial, Candidate, canonical, or
Product authority is granted.

## Correction gate

The first bounded coverage package exposed two upstream identity defects: SEC
Company Facts `fy` had been treated as an economic-cycle key, and Q2/Q3 origin
admission had required a separately labelled Q1 witness even though the YTD
facts carry their own start date. Its 114-ready / 82,326-blocked result is
retained as immutable diagnostic evidence, not governing coverage. ADR 0305
defines the required correction before another coverage build. No result from
that package gains downstream authority.

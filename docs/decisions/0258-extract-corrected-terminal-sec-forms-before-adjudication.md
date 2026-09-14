# ADR 0258: Extract Corrected-Terminal SEC Forms before Adjudication

## Status

Accepted.

## Context

The corrected-population content census proves that the retained Form 25-NSE,
8-K, and Form 15-12G can be parsed, but its lexical contexts are not form-aware
evidence. Directly adjudicating from keyword hits would collapse parsing,
candidate extraction, and fact decisions into one opaque step.

The original 219-document lane already has tested structured Form 25, Form 15,
and transaction-document extractors. Reusing those extractors avoids a second
interpretation vocabulary while keeping the new stable-ID population separate
from the historical 64-case sample.

## Decision

1. Formally bind the authoritative corrected-population plan, source package,
   and content census before extraction.
2. Require exactly the frozen one-case, three-document form set: one 25-NSE,
   one structured 8-K, and one 15-12G.
3. Reuse the established Form 25 table parser, Form 15 field parser, and 8-K
   transaction-scope parser without importing any historical case decision.
4. Preserve every physical/normalized source hash and require each extracted
   record to match its content-census record.
5. Retain all complete lifecycle fields as unsupported. Structured fields and
   contexts are candidates only and cannot assign a security, event, terminal
   date, consideration, or outcome.
6. Keep network, credentials, `/data`, lifecycle facts, outcomes, performance,
   Historical Coverage, research admission, Candidate, publication,
   deployment, and scheduler changes at zero.

## Consequences

The SCS case gains a deterministic form-aware candidate package that can feed
separate stable-ID-bound adjudication. It does not inherit any conclusion from
the earlier sample, and it cannot by itself reduce the terminal gap.

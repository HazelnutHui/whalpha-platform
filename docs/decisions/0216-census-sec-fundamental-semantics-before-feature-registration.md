# ADR 0216: Census SEC fundamental semantics before feature registration

- Status: Accepted
- Date: 2026-09-13

## Context

The retained SEC Company Facts foundation contains 41,619,407 normalized
five-year occurrences and conservative filing clocks. Completeness at that
source grain does not prove that two values are economically comparable.
Concept namespace, unit, instant/duration period, filing form, accession,
amendment, duplicate context, and later revision all affect meaning.

Building a fact-by-session panel or projecting every filer fact onto every
linked security before measuring those semantics would multiply ambiguous
records and make later correction expensive. The one-session filer/security
pilot is sufficient to measure representative common-stock filer coverage,
but it is later-observed diagnostic evidence and grants no historical issuer
projection.

## Decision

Build one immutable, owner-only SEC Company Facts semantic census before
registering any fundamental feature.

The census processes the existing sparse occurrence ledger exactly once. Each
normalized worker remains an independent process boundary. Within a worker,
filed-year Parquet streams are merged by their source occurrence order so all
rows for one `CIK + namespace + concept + unit` group can be evaluated without
loading the full source or creating a daily Cartesian panel.

The census distinguishes:

- source populations by filer, namespace, concept, unit, form, filing year,
  value kind, period shape, filing-clock state, and normalization state;
- the exact raw semantic key
  `CIK + namespace + concept + unit + start_date + end_date`;
- exact redundant occurrences within one accession and semantic key;
- different values within one accession and semantic key;
- ambiguous different values becoming available at the same timestamp across
  accessions; and
- clean later-accession revisions and value changes only when every involved
  occurrence is normalized, clock-admitted, uniquely valued within its
  accession, and chronologically unambiguous.

No conflict is resolved by row order. A conflicted or clock-incomplete
semantic key is excluded from clean revision statistics and counted
separately.

The report includes a bounded ranking of standard accounting concepts by
distinct filer coverage, then occurrence coverage. That ranking is discovery
evidence only: it does not create concept aliases, unit conversions, fiscal
period derivations, feature definitions, or model inputs. SEC-specialized and
unrecognized namespaces remain separately visible instead of being relabelled
as issuer extensions without evidence.

The existing one-session common-stock filer/security pilot may be bound as a
diagnostic population. Its matched-filer coverage is recorded, but neither
the link nor the census authorizes projecting issuer facts to a security or
backdating the observed relationship.

The completed package is outside canonical `/data`, immutable, deterministic,
and formally readable. It grants zero canonical, Membership, analytics,
Candidate, performance, publication, deployment, or scheduler authority.

## Consequences

- The first fundamental registry can be selected from measured semantics and
  residuals rather than popularity or intuition alone.
- Duplicate and revision counts have conservative, reproducible definitions.
- Processing remains proportional to source occurrences and bounded group
  state rather than occurrences multiplied by sessions.
- A later complete filer/security link can extend the coverage diagnostic
  without changing raw semantic definitions.
- The next stage remains a small registered concept/query layer; broad
  security projection and model use stay blocked.

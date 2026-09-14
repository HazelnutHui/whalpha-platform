# ADR 0257: Census Corrected-Terminal SEC Content before Adjudication

## Status

Accepted.

## Context

ADR 0256 retains three primary SEC documents for the case added by the
corrected EOD terminal population. Raw custody proves provenance and bytes,
but it does not prove that the files can be parsed or that a lifecycle field is
present, absent, matched, or conflicting.

The original 219-document lane already has a deterministic parser and eight
registered lexical marker families. Creating a different parser or marker
vocabulary for the corrected case would introduce avoidable semantic drift.

## Decision

1. Formally reread the authoritative corrected-population plan and complete
   source package before parsing any document.
2. Reuse the original deterministic decoding, markup normalization, date-token,
   field-marker, bounded-context, and hashing rules without adding a second
   vocabulary.
3. Require the plan, source manifest, completed source count, and ordered
   document count to agree before parsing.
4. Retain one immutable owner-only report with every document hash, normalized-
   text hash, parse profile, lexical counts, and at most three bounded contexts
   per field. Do not retain full normalized document text.
5. Treat every marker as an unresolved lexical candidate. A hit is not a fact;
   no hit is not proof of absence.
6. Keep network requests, credentials, `/data`, lifecycle facts, terminal
   outcomes, strategy labels, performance, Historical Coverage, research
   admission, Candidate, publication, deployment, and scheduler changes at
   zero.

## Consequences

The corrected case can move from byte custody to a reproducible content index
without weakening the established evidence boundary. Form-aware extraction
and field adjudication remain separate versioned stages.

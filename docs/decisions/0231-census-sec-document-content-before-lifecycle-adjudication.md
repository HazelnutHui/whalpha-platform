# ADR 0231: Census SEC Document Content Before Lifecycle Adjudication

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0230 retained all 219 transition-period SEC primary documents. Filing
presence and generic keywords are not lifecycle facts: boilerplate can contain
terms such as delisting, amendment, merger, or per-share consideration even
when the document does not establish the exact security-level field needed by
the first strategy.

The package contains ordinary HTML, SEC SGML-wrapped HTML, and inline-XBRL
XHTML. Before extracting candidate values or adjudicating evidence, the system
needs one reproducible view of parseability, document shape, and where each of
the eight registered field families has lexical support.

## Decision

1. Formally reread the complete ADR 0230 package and its exact plan with network
   access disabled.
2. Decode through a fixed UTF-8, UTF-8-BOM, then Windows-1252 order. Parse all
   HTML profiles with one standard-library parser, exclude script/style text,
   normalize Unicode and whitespace, and retain text hashes and counts.
3. Freeze one explicit regular-expression family for each of ADR 0223's eight
   lifecycle fields. Bind the complete ruleset fingerprint to the result.
4. Retain total occurrences and at most three bounded context windows per
   document and field. Do not duplicate the full normalized document text.
5. Label every hit `unresolved_lexical_candidate_only`. A missing marker is not
   evidence that an event or field is absent, and a hit is not a matched fact.
6. Preserve CIK, accession, plan time, and stable-ID locator for traceability,
   while keeping listed-security assignment, lifecycle fact, terminal outcome,
   Historical Coverage, research admission, Candidate, and Production counts
   fixed to zero.

## Consequences

- The next extraction stage can focus on measured document/form/field regions
  without repeatedly scanning or hand-selecting filings.
- Rule false positives remain visible and cannot silently become canonical
  facts.
- The census is a bounded intermediate evidence artifact, not another general
  document search platform.

## Rejected alternatives

### Promote keyword hits directly

Rejected because boilerplate, transaction proposals, amendments, and completed
events cannot be distinguished by occurrence alone.

### Retain a second full-text copy

Rejected because the immutable source bytes already exist; bounded contexts
and hashes are sufficient for deterministic candidate localization.

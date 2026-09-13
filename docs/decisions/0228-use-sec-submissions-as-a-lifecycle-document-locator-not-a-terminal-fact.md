# ADR 0228: Use SEC Submissions as a Lifecycle Document Locator, Not a Terminal Fact

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0223 froze 64 Strong-Leader Pullback lifecycle cases whose five-session
label paths cross their last canonical price observation. Every case has one
CIK locator, but a CIK identifies a filer rather than a listed security and
does not establish a last trade, delisting, successor, consideration, OTC
continuation, or terminal return.

Dell already retains a formally validated SEC Submissions bulk snapshot. Its
filing metadata includes form, filing and acceptance times, structured 8-K
items, accession, and primary-document locator. This is real official
second-source evidence, but the metadata alone is not the requested security-
level lifecycle fact.

## Decision

Build one network-prohibited, outcome-blind SEC metadata pilot over all 64
frozen lifecycle cases.

1. Bind the result to the exact ADR 0223 sample, SEC Submissions source
   package, and full-payload census.
2. Require exactly one CIK locator and its root member for every case. Read all
   referenced historical shards and reject missing, duplicated, malformed, or
   inconsistent source members.
3. Retain candidate filing locators across the declared five-year source range
   for direct lifecycle forms, selected transaction forms, structured 8-K
   items 1.03, 2.01, 3.01, 5.01, or 8.01, and post-last-observation 6-K
   reports.
4. Preserve the relation of every candidate filing to the canonical last
   observation and provider delisting-date candidate. Do not rank cases or
   omit pre-transition documents that may later explain a merger or other
   termination.
5. Treat accession and CIK as separate identifiers. An accession prefix is not
   required to equal the filer CIK.
6. Mark every complete security-level lifecycle field `unsupported` at this
   metadata layer. Form presence and a document locator are evidence-discovery
   results, not identity assignments, event facts, or terminal outcomes.
7. Keep the result in immutable owner-only research custody outside `/data`.
   It grants no document request, credential read, canonical write, Historical
   Coverage, research admission, outcome access, Candidate use, publication,
   deployment, or scheduler change.

## Consequences

- SEC can reduce the 64-case lifecycle search to an exact, auditable set of
  official filing documents without being misrepresented as a consolidated
  exchange lifecycle feed.
- A later document-acquisition and extraction stage can be bounded to the
  retained locators and separately decide what each document actually proves.
- Form 25, Form 15, 8-K, proxy, tender, and transaction filings remain
  candidates until their contents and security identity are reviewed.
- A commercial source remains useful for complete last-tradable dates,
  revisions, successor/consideration, and terminal-return coverage, but SEC
  evidence can independently corroborate a measured subset.

## Rejected alternatives

### Treat Form 25 filing date as the last tradable date

Rejected because filing, effectiveness, suspension, and last trading are
different facts.

### Treat a CIK match as stable security identity

Rejected because one issuer can have multiple listed securities and security
classes.

### Search all SEC filings for all historical instruments

Rejected because the first strategy already supplies a finite, outcome-blind
64-case acceptance population.

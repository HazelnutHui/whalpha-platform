# ADR 0255: Freeze New Terminal-Population SEC Sources before Acquisition

## Status

Accepted.

## Context

ADR 0254 adds one stable-ID case to the first strategy's corrected five-session
terminal population. That case did not belong to the immutable 64-security
source sample or its 219-document SEC package. Extending the old package would
erase its population boundary, while a ticker-led search could silently assign
the wrong issuer or security.

The retained lifecycle shadows link the new stable ID to point-in-time source
locators, and the formally retained SEC Submissions snapshot contains finite
filing metadata around its corrected last-EOD boundary. The project needs a
versioned bridge between those two evidence chains before any new request.

## Decision

1. Bind the authoritative terminal-gap V2 report, every lifecycle shadow used
   to recover the new stable ID, and the formally reread SEC Submissions source
   plus payload census.
2. Recover CIK, exchange, effective-date candidate, and selected stable
   identity only through the lifecycle decision/source fingerprint chain.
   Ticker is retained as a locator and grants no identity authority.
3. Select only direct lifecycle forms or structured lifecycle 8-K filings on
   or after the case's corrected last stable-ID EOD presence.
4. Freeze exact CIK/accession/document URLs, filing and acceptance times,
   request order, a two-request-per-second ceiling, two retries, and a 64-MiB
   per-document ceiling in one immutable owner-only plan.
5. Keep network requests, credential reads, document content, security facts,
   terminal outcomes, research admission, Candidate changes, publication,
   deployment, and scheduler changes at zero.

## Consequences

The newly discovered case receives its own auditable source boundary instead
of borrowing evidence from the old sample. A separate, explicitly governed
acquisition may consume the plan later. The plan itself cannot adjudicate a
transaction, cessation time, consideration, or strategy return.

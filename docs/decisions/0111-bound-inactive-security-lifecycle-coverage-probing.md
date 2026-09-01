# ADR 0111: Bound inactive-security lifecycle coverage probing

## Status

Accepted.

## Context

ADR 0110 established technical access to active Tickers and action endpoints,
but did not test `active=false`, pagination or lifecycle-field presence. A full
Historical Pilot is too broad for this question.

## Decision

Add a separate inactive-Tickers probe for one exact anchor date. It requests at
most two pages at 1,000 rows per page, follows only the same allowlisted path and
host, removes any API-key query value, uses 15-second serial pacing and performs
no retry.

Only aggregate counts survive: rows, pages, pagination completion, inactive/
conflicting/missing active flags, duplicate ticker count, and presence counts
for delisting/update/CIK/FIGI fields. No ticker, identifier or response body is
persisted or printed. Execution requires an acknowledgement bound to the clean
Git revision, date, contract, page size and request ceiling.

## Consequences

- The probe can distinguish accessible inactive evidence from evaluation-ready
  lifecycle coverage.
- Two full pages with another `next_url` report `truncated_at_ceiling`; they do
  not silently claim complete pagination.
- Ticker Events, merger terms, successors, last tradable sessions and delisting
  reasons remain outside this probe.
- The probe grants no Historical Pilot, Apply, publication or coverage authority.

# ADR 0112: Census inactive pagination within the Pilot ceiling

## Status

Accepted.

## Context

The first ADR 0111 run filled two 1,000-row pages and still had another page.
Historical Pilot design already reserves at most six inactive-Tickers requests,
so an exact page census can answer whether that ceiling is sufficient without
starting acquisition.

## Decision

Add a distinct six-page census contract while preserving ADR 0111's two-page
contract unchanged. It reuses the same exact anchor, `active=false`, 1,000-row
page, same-host/path, no-retry, 15-second serial and aggregate-only controls.
Its acknowledgement is independently bound to the clean source revision, date,
contract and six-request ceiling.

Natural pagination completion is reported only when `next_url` disappears. A
sixth page with another `next_url` remains `truncated_at_ceiling`. No response
body, identifier or ticker is retained or printed.

## Consequences

- The result can determine whether the existing six-request Pilot allocation
  is sufficient for this anchor.
- Complete pagination is collection evidence, not lifecycle completeness.
- Terminal reason, last-tradable session, merger consideration and successor
  identity remain separate required facts.
- No Pilot, Apply, publication, model or performance authority is created.

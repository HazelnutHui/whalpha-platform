# ADR 0236: Adjudicate SEC Cover Identity with Point-in-Time Tuples

- Status: Accepted
- Date: 2026-09-13

## Context

The 64-case coverage census leaves all 512 lifecycle fields unsupported. All
62 retained Form 8-K documents, however, contain inline-XBRL cover facts for
registrant CIK, report date, security title, trading symbol, and exchange.
Those structured facts can test the sampled listed-security identity without
interpreting narrative transaction language.

A global ticker join would still be unsafe. One later IPG Form 8-K reuses the
same ticker after the sampled common equity's provider delist-date candidate
and concerns a debt exchange. One TGI cover also discloses Purchase Rights
without a trading symbol. Neither record should be forced into the sampled
common equity.

## Decision

1. Parse only registered inline-XBRL cover facts and pair security title,
   ticker, and exchange by exact `contextRef`.
2. Normalize only observed Nasdaq and New York Stock Exchange names to their
   fixed MICs. Unknown exchange text fails closed.
3. Resolve identity through the existing point-in-time SEC identity resolver.
   Require a unique active CIK+ticker+exchange match and a common-equity cover
   title; ticker alone is forbidden.
4. Bound every source identity from first canonical observation through the
   provider delist-date candidate, inclusive. Preserve later same-ticker
   filings as outside-window evidence.
5. Retain incomplete non-target security contexts explicitly. Never borrow a
   ticker from an adjacent row or merge rights, debt, or preferred securities
   into common stock.
6. Mark only the stable-security/listing field for the 61 structured cases as
   `matched`. Keep all remaining fields unsupported and all canonical,
   lifecycle, terminal, research, Candidate, and Production authority false.

## Consequences

- Sixty-one lifecycle cases now have a reproducible event-time link between
  the stable source instrument and the SEC common-equity document.
- The later IPG debt-exchange filing is excluded by time rather than a company
  name heuristic.
- Transaction completion, dates, consideration, parties, last tradability,
  and terminal returns remain separate adjudication stages.

## Rejected alternatives

### Match every 8-K sharing CIK or ticker

Rejected because issuer filings can concern a different security or occur
after the sampled listing has ended.

### Drop incomplete or non-common cover rows

Rejected because silent deletion would hide whether parsing or source
structure created the apparent unique match.

# ADR 0238: Link Listing-Termination Reason without Inferring Terminal Date

- Status: Accepted
- Date: 2026-09-13

## Context

The 61 typed issuer transaction events establish when a merger or acquisition
completed but do not alone establish why or when the sampled common-stock
listing ended. Every corresponding Form 8-K contains one bounded Item 3.01
delisting section, but its text mixes completed, requested, anticipated, and
future-effective exchange actions.

## Decision

1. Reuse only the 61 stable-ID-linked transaction documents and bind every
   termination decision to its identity and transaction-event fingerprint.
2. Recognize a unique Item 3.01 section only from an exact heading or standard
   title. Exclude cross-item references from heading detection.
3. Require the section to contain transaction/acquisition, completion/causal,
   and listing/trading-action evidence before selecting
   `merger_or_acquisition`.
4. Retain observed action categories, but do not infer whether a request,
   intention, halt, suspension, Form 25 filing, or delisting was effective.
5. Keep effective delisting, first/last tradability, terminal return,
   consideration, party relations, canonical lifecycle, research, Candidate,
   and Production authority at zero.

## Consequences

- The listing-termination cause can be tested independently from the issuer
  completion date and market-status timing.
- Wording about future or requested exchange action cannot silently become a
  last-trading or terminal-return date.
- Consideration and party relations remain separate typed stages rather than
  being inferred from the cause label.

## Rejected alternatives

### Treat any merger 8-K as proof of listing termination

Rejected because issuer completion does not prove that the sampled security
was removed from trading or that the removal was caused by that event.

### Use the Form 25 or Item 3.01 filing date as last tradable date

Rejected because filing, requested halt, effective delisting, and exchange
trading sessions are distinct facts.

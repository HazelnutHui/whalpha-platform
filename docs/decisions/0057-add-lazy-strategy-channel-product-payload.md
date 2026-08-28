# ADR 0057: Add a Lazy Strategy-Channel Product Payload

## Status

Accepted

## Date

2026-08-28

## Context

The fixed Candidate strategy-channel preview now has an independent Oracle and
formal temporary-root audit. The existing Snapshot 1.8 Candidate projection
already reduces first load by separating a compact list summary from on-demand
security detail. Embedding strategy evidence in either file would increase
first-load cost or duplicate the same channel explanation across shards.

The three implemented technical channels remain mechanically verified but not
chronologically validated. Three additional channels are explicitly
unavailable. The product must not turn provisional channel scores into a new
cross-strategy total or a buy signal.

## Decision

Add a separate language-neutral `candidate-strategy-channels.json` product
payload. Snapshot 1.9 / Dashboard 2.6 may declare this file as an additive,
lazy-loaded Candidate resource while retaining the Snapshot 1.8 summary and
detail files unchanged.

The payload carries complete status counts and at most eight Advance/Watch
assessments per channel for each Universe. Each displayed assessment preserves
its score meaning, supporting evidence, counterevidence, first rejection risk,
reviewability condition, invalidation, manual checks, market-fit state, and
source fingerprints. It binds the exact strategy audit, Candidate publication,
Candidate batches, Entry Geometry batches, parameters, consumers, and zero-
mismatch Oracle gates.

The browser fetches this payload only when the strategy view is selected. It
performs schema and source-binding validation but no score, status, rank, or
reason calculation. The interface must:

- label the baseline as unvalidated and research-only;
- compare securities only inside one strategy channel;
- lead with why surfaced, chase/first-rejection risk, and what must happen next;
- show unavailable channels as unavailable rather than hiding or proxy-filling
  them;
- provide identical content to guest and credential Sessions.

Snapshot 1.8 and older releases remain readable. Repository implementation,
review builds, publication, and deployment remain separate actions.

## Consequences

- Strategy expansion does not enlarge the default Candidate list transfer.
- One small payload can serve all six channel tabs without opening Candidate
  detail shards.
- Full-population deprioritized rows remain in the Dell audit and do not cross
  the web-serving boundary.
- The UI can explain current mechanical routing, but it cannot claim win rate,
  expected return, option return, or calibrated confidence.

## Alternatives Considered

### Add channel fields to every Candidate summary row

Rejected because the first screen would download strategy data even when the
user never opens the strategy view.

### Copy channel explanations into Candidate detail shards

Rejected because top channel results can include securities outside the
bounded Candidate publication, and duplicated explanations complicate custody.

### Recalculate channels in React

Rejected because financial logic belongs on Dell and must remain independently
auditable and source-bound.

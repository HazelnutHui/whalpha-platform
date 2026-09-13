# ADR 0217: Compose Identity Evidence for Five-Year Corporate-Action Resolution

- Status: Accepted
- Date: 2026-09-13

## Context

The complete retained Massive corporate-action baseline covers 2021-08-11
through 2026-09-09: 6,491 split rows and 235,751 dividend rows. The original
resolution shadow required one Identity family-evidence manifest whose first
and last sessions exactly matched the source query boundary. That assumption
is stronger than the resolution rule requires and no longer matches the
available canonical evidence:

- the reconciled five-year Identity evidence contains 1,234 sessions from
  2021-09-13 through 2026-08-12; and
- the existing rolling Identity evidence contains 304 sessions from
  2025-06-23 through 2026-09-04.

Their 287 overlapping sessions bind identical artifacts. Source observations
outside the combined exact-session set must remain quarantined; inventing an
Identity row for a warm-up, holiday, weekend, or unevidenced tail date would
be worse than retaining the gap.

The old shadow output was also restricted to `/tmp`. Rebuilding a complete
five-year mapping after every reboot would waste already validated evidence
and could obscure which source observation was used.

## Decision

Extend the resolution-shadow implementation without changing its row schema or
authority:

1. A build may bind one or more formally published
   `point_in_time_identity` family-evidence manifests.
2. Every Identity session must fall inside the corporate-action source range.
   Overlapping evidence is accepted only when the complete artifact binding is
   identical; any conflict stops the build.
3. The combined session set is ordered and unique. Resolution still uses only
   the provider ticker in the exact event-date Resolver. Missing dates and
   missing tickers remain separate quarantine reasons.
4. Contract 1.0 remains readable. Contract 1.1 records every evidence
   manifest binding, combined coverage boundaries, overlap count, and a literal
   zero overlap-conflict count.
5. A 1.1 output may be retained beneath one explicitly supplied owner-only
   Dell candidate directory. The target must be a direct child of that exact
   real mode-0700 directory; symlinks, broader roots, nested targets, and mode
   drift fail closed. Legacy 1.0 `/tmp` behavior remains unchanged.
6. Contract 1.1 must account for every source row. Rows representable by the
   provider-neutral observation schema enter year-partitioned Parquet. A row
   lacking required typed identity, such as provider ticker, is retained in a
   separately hashed `unrepresentable.json` quarantine record containing its
   source kind, event date, observation time, reason, optional provider action
   ID, and payload fingerprint. It is neither dropped nor repaired with a
   sentinel ticker. Typed rows plus quarantine records must equal source rows.
7. The first five-year build uses the retained baseline split and dividend
   packages. The separate repeat diffs remain required revision evidence. In
   particular, the five removed and five added split IDs are not collapsed
   into revisions or resolved by economic-payload similarity at this stage.

## Consequences

- The complete source population can be mapped once against all currently
  published exact-date Identity evidence and formally reread from durable
  private custody.
- A larger resolved count does not make the result canonical Corporate Action,
  an Adjustment Ledger, signal-time evidence, Historical Coverage, research
  input, Candidate input, or Production input.
- The combined evidence may still end before the source range. Those rows stay
  visible as `event_date_identity_unavailable` until separately published
  Identity evidence exists.
- Provider action-ID instability remains a named promotion gate rather than a
  reason to discard otherwise useful baseline-resolution evidence.
- A nonzero unrepresentable count makes typed mapping one-to-one false while
  complete source accounting remains true. Such rows stay a promotion blocker.

## Acceptance boundary

The change is complete when focused tests prove legacy 1.0 compatibility,
multi-evidence overlap acceptance, overlap-conflict refusal, subset coverage
quarantine, explicit accounting of unrepresentable rows, exact persistent-root
enforcement, and formal reread; then a real five-year baseline build must
account for every retained source row and complete with zero network, `/data`,
analytics, publication, deployment, or scheduler activity.

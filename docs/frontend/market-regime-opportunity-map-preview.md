# Market Regime & Opportunity Map Local Preview

## Implemented desktop surface

The local Dashboard now has a `Regime & Opportunity Map` view selected by
`view=regime`. It renders only the configured preview API payload and performs
no financial calculation in React.

The page contains:

1. a Market State hero with selected Universe, as-of session, Candidate,
   Confirmed state, Composite, key support/conflict, data status, and research
   disclaimer;
2. five expandable dimension cards showing score, configured/effective weight,
   contribution, raw metrics, normalization, and reason codes;
3. four fixed-priority relationship highlights (non-neutral state priority,
   then immutable registry order);
4. all 16 relationship rows with 5/10/20-session selection, family/state
   filters, non-neutral scope, and clear action;
5. a pair drawer with both legs, relative spread, correlation/change, ratio
   availability, evidence, counterevidence, reason codes, and interpretation
   boundaries;
6. methodology, source fingerprints, and short-history limitations.

The selected window, Universe, filters, and pair ID use URL query parameters.
Valid direct links, refresh, and browser back/forward reconstruct the view.
Common Shares remains first and default. Switching to Common Shares + ADRs
loads that separate regime ledger; the ETF facts do not change.

## Presentation boundary

- Positive/negative color is accompanied by signed numbers and state text.
- State has text, a marker, and restrained color.
- Raw reason codes remain available in expansions; primary copy is generated
  by deterministic label rules.
- A relative spread is always visible beside the relationship state, including
  cases such as IGV/QQQ where a synchronous label alone would hide relative
  resilience.
- Missing 60-session ratio statistics say that at least 60 sessions are
  required; they never render as zero.
- The page says explicitly that relationship statistics are non-causal,
  price relationships are not fund flow, and the preview is not a trade
  recommendation or backtest.

This is desktop-first. At narrower desktop widths cards reduce columns without
horizontal page overflow. Below 820px, the relationship table alone may scroll
horizontally while the page and interpretation remain usable.

## Non-production status

This page is available only in a local application started with an explicit
`/tmp` preview bundle. It is absent from the current Production Dashboard,
static snapshot, OCI bundle, and `whalpha.com`. Existing session protection is
unchanged. Future guest and authenticated users must consume the identical
analytics payload with the same fields, precision, and as-of session.

# ADR 0253: Separate Identity Observation from EOD Terminal Boundaries

## Status

Accepted.

## Context

ADR 0221 deliberately measured lifecycle paths against the last date on which
a stable ID appeared in canonical Instrument Master history. Its contract
called that field `canonical_last_observed_date`, retained it only as a source-
acquisition diagnostic, and explicitly denied that it was a last-tradable or
terminal fact.

ADR 0252 later reused those path counts as the population and impact measure
for terminal evidence. A direct read of canonical EOD exposed the semantic
error: Instrument Master `as_of_date` describes provider identity state, not
price-bar presence. Equality is possible but not guaranteed. A terminal-gap
count cannot use the identity observation date as if it were an EOD boundary.

The original blocker census remains correct for its declared diagnostic role.
Rewriting it would erase lineage. The terminal interpretation and its frozen
64-security sample, however, require a versioned correction before further
source work or research admission.

## Decision

1. Preserve the ADR 0221 blocker census and source sample as historical,
   outcome-blind source-priority evidence. Do not relabel their identity-span
   counts as terminal EOD counts.
2. Reconcile every lifecycle row in the blocker census, not only the prior
   64-security crossing sample, against canonical stable-ID EOD presence from
   the first registered signal session through five exchange sessions after
   the last registered signal session.
3. Formally validate each EOD partition, its content fingerprint, physical
   Parquet hash, and bound Identity snapshot. Materialize only the requested
   stable-ID presence set after validation; do not join a current ticker or
   reopen unrelated values.
4. Rebuild the exact registered 1/3/5-session path crossings twice: once from
   the retained identity-observation proxy and once from the EOD presence
   boundary. Require the former to reproduce the ADR 0221 manifest exactly.
5. Keep `canonical_identity_last_observed_date` and
   `strategy_window_last_eod_observed_date` as separate fields. Neither alone
   proves a legal last-trading date, transaction outcome, terminal return, or
   adjustment policy.
6. Retain one immutable, owner-only, network-disabled correction report outside
   `/data`. It may supersede downstream terminal-gap counts, but it grants no
   canonical data, Historical Coverage, research admission, Candidate,
   publication, deployment, or scheduler authority.
7. Version the terminal-gap population after this correction. Any newly in-
   scope stable ID must enter a complete source/evidence workflow rather than
   being silently dropped or ticker-matched into the old sample.

## Consequences

- Terminal source work is measured against actual canonical EOD presence
  instead of an identity-state proxy.
- The old terminal-gap report remains immutable evidence of what the prior
  rule calculated, but its population and path counts are no longer current
  authority.
- The correction adds one bounded formal read over the registered strategy
  window. It avoids a five-year value scan and does not calculate returns.
- Further cessation, complex-payoff, or research-admission work must bind the
  corrected population.

# Five-Year Corporate-Action Resolution

This runbook builds and rereads the private ADR 0217 exact-event-date
resolution candidate. It performs no network request, `/data` write, canonical
Corporate Action or Adjustment Ledger publication, analytics, deployment, or
scheduler change.

## Preconditions

- Run on Dell as the repository owner from clean `main`.
- Use the complete retained baseline split and dividend packages with their
  exact shared custody parent.
- Pass only published `point_in_time_identity` evidence manifests below the
  canonical Dell data root.
- Confirm every overlap binds identical artifacts and every evidence session
  is inside the source range.
- Create one exact owner-only mode-0700 output parent outside `/data`; the
  target must be its absent direct child.

## Build

Invoke the module with the exact date range, source packages, each Identity
evidence path as a separate `--identity-evidence` argument, the source custody
root, output custody root, absent output child, a fixed UTC materialization
time, and `--execute`.

Review only aggregate output: mapped plus unrepresentable counts must match
source rows exactly; typed mapping may be false only when the explicit
unrepresentable quarantine is nonempty;
overlap conflict count must be zero; resolved and quarantined totals must sum
to mapped rows; missing exact-date Identity, unresolved ticker, and typed-
mapping failures stay separate. The CLI does not print provider payloads.

## Reread and failure handling

Reread with the same exact output custody root. A rerun with identical inputs
and time must return `already_present`. A conflicting target, unsafe path,
evidence change, overlap conflict, non-one-to-one mapping, or unrepresentable
source row stops without replacement or cleanup.

Keep the separate baseline/repeat diff packages. Five split IDs changed while
their non-ID economic payload did not; this run does not reinterpret those ID
changes. Do not use the candidate for return adjustment or model research
until the subsequent event-identity and adjustment gates pass.

## Derived split-adjustment review candidate

The disconnected split-adjustment candidate may reread the persistent shadow
only when both the exact build path and its approved custody root are supplied:

```bash
scripts/dev/run-project-python.sh \
  -m tip_api.services.historical_split_adjustment_candidate_cli \
  --resolution-shadow <exact-persistent-shadow-build> \
  --resolution-shadow-custody-root <exact-owner-only-shadow-custody-root> \
  --output-root <absent-direct-child-below-tmp> \
  --basis-session <shadow-end-session> \
  --calculated-at <fixed-utc-time> \
  --execute
```

The output groups only resolved split-like rows by stable `instrument_id` and
event date, composes known ratios, and separately projects possible impacts of
unresolved tickers without assigning those events. It remains owner-only,
temporary, outcome-reconciliation evidence with no canonical write,
Adjustment Ledger status, research-input authority, or neutral-absence claim.

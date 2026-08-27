# ADR 0023: Preserve Market Regime State Prefix Across As-Of Sessions

## Status

Accepted

## Date

2026-08-27

## Context

Phase 1b previously replayed state from the six Composites available inside
each day's exact 26-session Phase 1a source panel. Moving from 2026-08-25 to
2026-08-26 dropped the oldest source session and therefore dropped the oldest
Composite before bootstrap. Historical confirmed states, confirmation counts,
threshold semantics, and row fingerprints changed even though no historical
EOD partition changed.

The existing future-prefix test replayed a prefix and full sequence inside one
fixed input panel. It did not compare independently generated adjacent as-of
audits, so it did not detect the rolling-left-boundary defect. Candidate daily
incremental calculation exposed the issue because a valid 2026-08-25 Candidate
audit could not bind the recalculated 2026-08-25 Phase 1b rows in the
2026-08-26 audit.

## Decision

Phase 1b cold replay starts from the first contiguous canonical EOD session
retained by the formal Dell repository and keeps that left boundary stable as
new sessions are appended. Each individual Phase 1a Composite still uses at
most its exact trailing 26-session source window, so its current-session values
and source fingerprint remain compatible with the separately approved Phase
1a audit.

The corrected state calculation is
`market-regime-opportunity-map-state-v1.0.1` with parameter set
`mrom-regime-state-v1-stable-prefix-2`. The parameter contract explicitly
includes the stable history-start policy, 26-session Composite source window,
and cross-as-of future-prefix requirement. The legacy V1.0.0 audit and typed
records remain readable but are not eligible as a prefix for the corrected
Candidate incremental path.

Adjacent corrected Phase 1b audits must prove that every record through the
prior as-of is byte-logically identical. A later daily Phase 1b incremental
mode should append one current Composite to a formally verified prior audit;
the stable-prefix cold replay remains the reference.

## Consequences

- Historical state is no longer reinitialized when the rolling Phase 1a
  window advances.
- Corrected Phase 1b and downstream Candidate results require a new offline
  rebaseline before any publication consideration.
- Existing Production publications and OCI artifacts remain unchanged and
  continue to bind their original legacy audits.
- Cold Phase 1b replay grows with retained canonical history. A verified-prior
  one-session append is now the next upstream performance requirement.
- Data retention must preserve either the original state anchor inputs or a
  formally verified prior state audit; silently truncating both is forbidden.

## Alternatives Considered

### Treat each rolling 26-session state replay as a new independent history

Rejected because state machines require chronological continuity and the same
historical session cannot legitimately change without a source or model
revision.

### Ignore changed Phase 1b fingerprints in Candidate incremental execution

Rejected because the differences included confirmed state and transition
semantics, not merely container metadata.

### Use all prior observations in every Phase 1a Composite

Rejected because it would change the fixed trailing-window Phase 1a source
contract and break compatibility with the separately approved current
Composite audit.

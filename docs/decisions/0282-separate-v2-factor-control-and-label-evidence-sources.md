# ADR 0282: Separate V2 Factor, Control, and Label Evidence Sources

## Status

Accepted

## Date

2026-09-15

## Context

ADR 0280 admitted a private five-year split candidate to repair the
outcome-blind Factor Catalog V2 qualification. ADR 0281 then bound the frozen
Development screen to that exact qualification, but did not state whether the
private extension could be reused when reconstructing the qualified factor
measurements or when building the nuisance control and future labels.

ADR 0281 also reuses V1's 106-session complete-factor Development cohort, not
all 118 chronologically usable raw Development sessions. That distinction must
be reconstructed from the exact frozen V1 diagnostics rather than inferred
from dates alone.

The distinction is material. The 126-session factor window starts before the
canonical split publications and cannot reproduce the admitted qualification
without the exact ADR 0280 evidence. By contrast, every 20-session nuisance
control window and every 1/3/5-session Development outcome path starts after
canonical split coverage begins. Letting the private extension alter those
controls or outcomes would exceed its necessary scope and obscure provenance.
No V2 Development outcome has been read while making this decision.

## Decision

1. Preserve the statistical protocol, trial budget, labels, gates, cohort,
   stopping rule, and logical fingerprint accepted by ADR 0281.
2. Require the exact V1 diagnostics bound by the V1 screening protocol and use
   its complete `relative_return_spy_20s` session evidence to reproduce the
   frozen 106-session / 167,860-path cohort. The report must bind that
   diagnostics logical fingerprint, physical SHA-256, and its own Membership
   fingerprint. Raw Development dates alone are insufficient; the V1
   diagnostics Membership fingerprint must not be conflated with V2's distinct
   qualification-population fingerprint.
3. Narrowly extend ADR 0280 so the V2 screen may recompute factor observations
   with the exact qualification-bound private split extension. The runner must
   first reproduce the complete qualification report byte-for-byte in memory;
   any factor-evidence, population, implementation, or qualification mismatch
   stops before a result is written.
4. Use only the canonical split-action and split-adjustment publications for
   the signal-inclusive 20-session `relative_return_spy_20s` nuisance control.
   The private extension must not change that control.
5. Use only canonical EOD, canonical split-action and split-adjustment
   publications, and the already governed terminal-reference chain to build
   1/3/5-session Development labels. The private extension must not construct,
   complete, or alter a future outcome.
6. The immutable V2 report must carry separate factor, control, and label
   action/adjustment fingerprints. It must also bind the exact ordered
   observation, control, and label collections through separate fingerprints,
   plus calculation-code hashes and one committed implementation revision.
7. Missing or conflicting evidence remains a stable-ID-specific nonnumeric
   exclusion. Nothing may be zero-filled, silently inferred, or converted from
   an interval to a point estimate.
8. Preserve one immutable report and one exact replay. This decision grants no
   Validation, Holdout, Model Construction, Strategy Expression, Candidate,
   canonical-data, network, publication, deployment, broker, or trading
   authority.

## Consequences

The Development screen can reproduce the factor values that actually passed
qualification without allowing qualification-only evidence to leak into
forward returns. The result remains reconstructed latest-vintage research, not
an `as_operated` history. Distinct collection fingerprints make an apparently
identical aggregate report fail replay if any underlying observation, control,
label, missingness state, terminal interval, or source identity changes.

## Rejected alternatives

- Apply the private five-year split candidate to controls or future labels.
- Recompute long-window factors from canonical-only evidence and silently
  change the qualified factor population.
- Record one undifferentiated action/adjustment fingerprint for all inputs.
- Change the frozen statistical gates or outcome definitions while resolving
  an evidence-provenance ambiguity.

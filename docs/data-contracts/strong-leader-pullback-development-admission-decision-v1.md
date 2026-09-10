# Strong-Leader Pullback Development Admission Decision V1

## Purpose

This contract implements ADR 0195 by turning one formally reread,
outcome-blind coverage census into an immutable missingness-only decision. It
does not run a strategy, select parameters, or authorize research execution.

## Frozen rule

- Admission unit: one complete Primary session cross-section.
- Completeness threshold: 100%, represented as 10,000 basis points.
- Minimum history: 252 admitted sessions, inherited from the preregistered V1
  experiment.
- One incomplete included path excludes the entire session.
- Zero-included sessions are not admissible.
- Missing and quarantined records remain in the denominator.
- Coverage-based stable-ID selection is prohibited.

The decision binds the census contract, policy, source revision, logical
fingerprint, physical SHA-256, fixed interval, and the frozen experiment ID and
fingerprint.

## Current version

Version 1.0 can only record `rejected_current_evidence`. The bound census has
zero all-required-evidence-complete paths, so it cannot create an admitted
cohort. An eventual positive decision requires repaired evidence, a new census
contract, and a new admission-decision contract version.

Every decision fixes admitted sessions, paths, and instruments to zero and
fixes strategy triggers, forward outcomes, performance metrics, parameter
selection, development, validation, holdout access, Candidate activation,
external requests, canonical writes, and Production writes to false or zero.

## Custody

The network-disabled command formally rereads the census and writes one
canonical `decision.json` into a new owner-only direct child of `/tmp`. The
directory is mode `0700`; the file is mode `0400`; creation is exclusive and
atomic; canonical bytes and the typed contract are reread before completion.

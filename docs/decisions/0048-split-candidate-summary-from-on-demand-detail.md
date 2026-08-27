# ADR 0048: Split Candidate Summary from On-Demand Detail

## Status

Accepted

## Date

2026-08-27

## Context

The active 2026-08-26 Candidate snapshot is 20,367,627 bytes. The browser must
download and parse all 496 Primary and 532 Secondary full explanation records
before it can render a bounded Candidate list. Most bytes belong to component
metrics, evidence, state gates, invalidation conditions, and entry facts that
are needed only after a user opens one security.

Future strategy-specific Candidate channels will add classifications and
explanations. Expanding the monolithic file would make first load slower and
would encourage removing evidence to control size. Neither is acceptable.

## Decision

Add Snapshot 1.8 / Dashboard 2.5 as a backward-compatible consumer change.
Market Intelligence 1.2 and Candidate publication 1.1 remain unchanged.

Snapshot 1.8 writes one Candidate summary containing complete Universe, stage,
risk-mode, entry-lane, source, warning, and ranking metadata plus only the
fields required to render lists. Full cards are placed in deterministic detail
shards by Universe catalog position and the first hexadecimal character of
stable `instrument_id`.

Each summary row binds its exact score and entry-geometry fingerprints and one
declared shard. Each shard binds publication ID, full Candidate analytics
fingerprint, Universe, stable-ID prefix, item count, and its own logical
fingerprint. The Snapshot manifest freezes the summary contract/fingerprint,
every detail filename, every file SHA-256, and all existing Candidate/entry
source bindings.

The formal reader validates every file and losslessly reconstructs the original
`opportunity-candidate-publication/1.1`. Publication fails closed unless that
content validates against the original full logical fingerprint. The browser
loads only the summary initially and fetches one declared shard when a user
opens a detail drawer. A bounded eight-shard in-memory cache avoids repeat
downloads within one browser session and is keyed by publication ID so a new
publication cannot reuse old detail. React never recalculates a score, rank,
lane, or explanation.

Snapshot 1.5–1.7 remain rollback-compatible. No production publication or
deployment is part of this decision.

## Consequences

- The measured 2026-08-26 initial Candidate transfer falls from 20,367,627 to
  1,490,756 bytes, a 92.68% reduction.
- Thirty-two shards contain about 0.47–1.03 MB each.
- Total Candidate static bytes rise to 21,842,803 because the list projection
  intentionally duplicates a small subset of display fields. This roughly 7%
  storage cost is acceptable at the OCI static-serving boundary.
- Full explanations, counterevidence, raw metrics, parameters, state gates,
  invalidation codes, and fingerprints remain available on demand.
- Strategy-channel expansion can add compact routing fields without forcing
  all detail evidence into the first load.

## Alternatives Considered

### Remove raw facts and evidence

Rejected because explanation and auditability are core product requirements.

### Keep one separate 20 MB detail file

Rejected because the first opened stock would still download every detail.

### Publish one file per security

Rejected because more than one thousand small files would add excessive
manifest, deployment, and filesystem overhead.

### Recalculate detail in the browser

Rejected because it duplicates financial logic and weakens source binding.

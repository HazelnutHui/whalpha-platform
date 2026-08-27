# Candidate Snapshot Split Audit — 2026-08-27

## Scope

This development audit used the active, formally readable 2026-08-26 Market
Intelligence 1.2 payload and its Candidate publication 1.1. It built Snapshot
1.8 / Dashboard 2.5 only under `/tmp`. Production Snapshot 1.7 / Dashboard 2.4
was not changed.

## Result

| Measure | Verified value |
| --- | ---: |
| Original monolithic Candidate file | 20,367,627 bytes |
| New first-load summary | 1,490,756 bytes |
| First-load reduction | 92.68% |
| Detail shard count | 32 |
| Smallest detail shard | 474,940 bytes |
| Largest detail shard | 1,028,834 bytes |
| Total summary plus detail bytes | 21,842,803 bytes |
| Primary records | 496 |
| Secondary records | 532 |
| Snapshot private-data files | 38 |

Every summary row was tied to the exact score fingerprint, entry-geometry
fingerprint, stable-ID prefix, and one declared shard. The formal Snapshot
reader validated all file hashes and logical bindings, then reconstructed the
full `opportunity-candidate-publication/1.1`. The reconstructed typed model was
exactly equal to the source publication.

A second `/tmp` build used a 2026-08-26 post-close check time so formal XNYS
freshness was lag zero. Approval-plan construction returned plan 2.3 with
Snapshot 1.8 / Dashboard 2.5, `normal_freshness=true`, and all 32 ordered detail
files bound. Formal plan validation passed. This proved the publication contract
without applying the plan.

The additional total storage is the deliberate compact-list duplication cost;
no explanation, counterevidence, metric, state gate, invalidation code, or
source fingerprint was removed from on-demand detail.

## Safety boundary

The run read `/data` through existing formal readers and wrote only development
releases under `/tmp/whalpha-candidate-split-1yFKyA` and
`/tmp/whalpha-candidate-split-fresh-bDnBwa`. It made no
provider or other external request, accessed no credential, and performed no
canonical Apply, Market Intelligence publication, Snapshot activation, bundle
publication, OCI access, deployment, scheduler, or notification operation.

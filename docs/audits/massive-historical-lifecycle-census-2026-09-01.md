# Massive Historical Lifecycle Pagination Census — 2026-09-01

## Result

One exactly authorized census ran from clean Dell `main` revision
`65395d7deca9eef6a2bd75e524f06d478aea1c35` for anchor 2026-07-16.
All six 1,000-row pages were full and another page existed, so the census ended
`truncated_at_ceiling`.

| Aggregate fact | Count | Share of 6,000 rows |
| --- | ---: | ---: |
| Explicit `active=false` | 6,000 | 100.00% |
| Active-state conflict/missing | 0 | 0.00% |
| `delisted_utc` present | 5,879 | 97.98% |
| `last_updated_utc` present | 6,000 | 100.00% |
| CIK present | 5,017 | 83.62% |
| Composite FIGI present | 1,508 | 25.13% |
| Share Class FIGI present | 1,348 | 22.47% |
| Duplicate ticker occurrences | 48 | 0.80% |

There were six requests, no retry, no retained response body or identifier and
zero data writes. Result fingerprint:
`f6643417832e931f6928d28279e92750b441e5b970212af17ae23dd790d940cb`.

## Interpretation boundary

The Historical Pilot's six-request inactive allocation is insufficient for a
complete 2026-07-16 collection. Raising it inside the fixed 80-request Pilot
would compete with three-session active Identity, EOD and action evidence.
The next design review should separate a reusable immutable inactive/lifecycle
baseline from the three-session Pilot rather than silently expanding the Pilot.
Full pagination, lifecycle completeness, Pilot and Apply remain unauthorized.

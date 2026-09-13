# Strong-Leader Pullback Source Acceptance Sample — 2026-09-13

## Result

ADR 0223's provider-neutral, outcome-blind acceptance population is complete
in owner-only Dell custody. It was built from formal readers over the ADR 0221
blocker census and both retained inactive-lifecycle anchors. No provider was
contacted and no credential was read.

## Bound inputs

- blocker census:
  `strong-leader-pullback-evidence-blocker-census/build=20260913-v1`;
- inactive-lifecycle shadow:
  `inactive-lifecycle-resolution/build=five-year-20260912-v1`;
- source anchors: 2026-07-16 and 2026-09-03; and
- implementation revision:
  `6b7525b77e342792fa43d4766c8470536d078b43`.

The report contains three manifest/fingerprint bindings. Missing exact source
occurrence lineage rejects the whole package.

## Frozen population

| Measure | Result |
| --- | ---: |
| Unassigned action cases | 20 |
| Unique action source records | 20 |
| Candidate stable IDs for actions | 4 |
| Five-session lifecycle-crossing cases | 64 |
| Lifecycle source occurrences | 122 |
| Overlapping action/lifecycle IDs | 0 |
| Combined stable IDs | 68 |

All cases were retained without ranking, convenience sampling, or outcome
inspection. Action candidate IDs remain unassigned. Lifecycle ticker, FIGI,
CIK, name, exchange, and type values remain locators rather than terminal
facts.

## Output and validation

- output:
  `strong-leader-pullback-source-acceptance-sample/build=20260913-v1`;
- file: one canonical `sample.json`, 78,458 bytes;
- report SHA-256:
  `17a1c177be65693786a410c1c2107c499e34a88960541a24339644e12ba01416`;
- logical fingerprint:
  `f29da6a170f873b20a4ee57141cf1dc975f5a8f3a840dc19dc115283828c1a5a`;
- build wall time: 6.59 seconds;
- peak resident memory: 661,532 KiB; and
- permissions: directories `0700`, report `0400`.

Built-in and separate formal rereads returned the same report and both
fingerprints. Twenty-two directly related tests passed. There are no symlinks,
partial directories, or temporary files in the sample custody.

The complete API suite also passed 2,607 tests in 265.82 seconds. Its two
warnings are unchanged dependency deprecations for Python `crypt` and the
Starlette/httpx test adapter.

Stable-ID assignment, terminal outcomes, strategy triggers, forward outcomes,
metrics, parameter/cohort selection, provider requests, credential reads,
canonical writes, Historical Coverage, research admission, Candidate writes,
publication, deployment, and scheduler changes are all zero.

## Decision and next boundary

The former undirected global evidence search is closed for the first strategy.
A later source-specific pilot must be bound to this exact fingerprint, request
the frozen action/lifecycle fields, retain matched, absent, unsupported, and
conflicting results, and produce a measured gap matrix. No provider response
may assign identity, establish a terminal outcome, or admit research without a
separate reviewed decision.

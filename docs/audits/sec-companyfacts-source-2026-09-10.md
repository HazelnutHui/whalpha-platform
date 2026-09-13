# SEC Company Facts Source — 2026-09-10

## Scope

Acquire and formally reread one official SEC Company Facts bulk snapshot in
private Dell source custody. The run used clean revision
`c4c9d2b2b79e23e96c886b5aca1cc9e552778d70`, the configured owner-only SEC
User-Agent, serial access at no more than two requests per second, and no
canonical `/data`, analytics, Product, Production, or scheduler authority.

## Result

The remote object reported Last-Modified 2026-09-10 and was acquired in 11
consecutive 128-MiB-or-smaller ranges after one HEAD observation:

| Measure | Result |
| --- | ---: |
| Successful requests | 12 |
| Archive bytes | 1,408,478,936 |
| Archive SHA-256 | `88c5b850bbd8a9199c3419c3dc02098c606fd1ff1e697b7df9ba691f48679522` |
| Unique root-level CIK JSON members | 20,343 |
| Compressed member bytes | bound in manifest |
| Total uncompressed member bytes | 19,294,356,913 |
| Manifest SHA-256 | `c7ac1eaf45368c2cb285023f313007a274e1cbec063063f9d55a598e1466a77d` |
| Logical fingerprint | `d42cfcc44b090395d32c48b6be38d35490c67aa494f545a82aedfe39e0f3b261` |

Every archive/chunk hash, exact object/range identity, ZIP central-directory
constraint, unique CIK filename, member size/compression ceiling, file mode,
and exact package file set passed formal reread. The package is three mode
`0400` files in a mode `0700` directory; its sibling lock is mode `0600`.
No credential or response identifier is retained.

The full API regression passed 2,429 tests with two unchanged dependency
deprecation warnings after the live package was reread.

## Alignment decision

Source custody is complete. Full member decompression, CRC, JSON schemas,
concept/unit populations, amended facts, filing clocks, and the five-year
selection have not yet been validated; the manifest says
`deferred_to_normalization`. Therefore this package is not point-in-time
fundamentals and cannot make any research interval eligible.

The next bounded stage streams members directly from the archive, validates
each payload without creating a 19.29-GB extracted copy, and emits a sealed
five-year structural/missingness census. Exact acceptance time requires later
accession linkage to SEC submissions; `filed` date alone is not silently
treated as a same-day tradable timestamp.

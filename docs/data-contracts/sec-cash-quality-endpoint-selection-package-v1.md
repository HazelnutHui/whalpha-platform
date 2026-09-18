# SEC Cash-Quality Endpoint Selection Package V1

This closed-set owner-only package is an outcome-blind source-engineering
artifact between readiness census and TTM feasibility.

The immutable plan binds exact census plan/result/replay evidence, normalized
source manifest/content, filing clock, occurrence schema, source denominator,
target denominator, and the admitted ready-endpoint count. Budgets permit one
formal source reread, exactly the verified target rows, and three selected
query rows per ready endpoint.

`target-occurrence-index.parquet` retains only the three registered concepts,
including occurrence disposition, value text and kind, accession, fiscal
coordinates, filing and knowledge times, eligible session, and source
occurrence ID. `ready-endpoint-selections.parquet` contains only endpoints that
passed ADR 0302 readiness. Each endpoint has exact Assets, net-income, and CFO
rows; CFO and net income share a clean accession; duplicate occurrence IDs
supporting the selected state remain explicit.

The package manifest binds both Arrow schemas, row counts, byte sizes, physical
SHA-256 values, the selection plan, and zero downstream authority. Publication
uses an owner-only staging directory, fsync, atomic rename, immutable files,
closed-set inventory, and exact reread.

The linked TTM feasibility object is plan-only. Neither package creation nor
reread computes discrete quarters or TTM, projects onto a security, creates a
factor, reads outcomes, or changes research/Product authority.

See
[ADR 0303](../decisions/0303-persist-sec-cash-quality-readiness-and-build-reusable-endpoint-evidence.md).

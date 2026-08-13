# 0002: Separate Compute and Public Web Serving

## Status

Accepted

## Date

2026-08-12

## Context

The project needs both heavier market-data processing and public web serving. The available OCI instance has limited memory and should stay simple.

## Decision

The workstation handles compute and data. OCI handles whalpha.com and lightweight serving. Heavy market processing should be avoided on the small OCI instance.

## Consequences

- Compute-heavy jobs should run on `dell5820`.
- `whalpha-oci` should remain a web-serving boundary.
- Deployment must move only the required application artifacts or results to OCI.

## Alternatives Considered

- Run all compute on OCI: rejected because of resource constraints.
- Run public web serving from the workstation: rejected because OCI is the intended public boundary.

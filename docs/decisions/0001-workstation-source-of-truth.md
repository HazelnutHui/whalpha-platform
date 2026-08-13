# 0001: Use the Workstation as the Project Source of Truth

## Status

Accepted

## Date

2026-08-12

## Context

The project needs a stable source of truth for code, computation, and data processing. A desktop folder or manual copy would make state unclear and hard to reproduce.

## Decision

Code and computation live on `dell5820`. Windows desktop folders are not source-of-truth project copies. WSL/Codex accesses the workstation by SSH.

## Consequences

- Project work should happen on the workstation unless explicitly stated otherwise.
- Repository state should be clear and reproducible.
- Local desktop files should not become hidden production inputs.

## Alternatives Considered

- Keep the project on a Windows desktop folder: rejected because it weakens operational clarity.
- Use OCI as the primary development source: rejected because the instance is resource constrained and public-facing.

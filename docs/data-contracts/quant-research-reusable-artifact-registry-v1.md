# Quant Research Reusable Artifact Registry V1

## Purpose

`quant-research-reusable-artifact-registry/1.0` implements the first boundary
of ADR 0283. It defines how a research population, point-in-time market-state
panel, feature matrix, nuisance-control panel, or outcome-label panel may be
identified and reused without rebuilding the same deterministic input for each
factor campaign.

This is an infrastructure contract for the next Factor Discovery campaign. It
does not register that campaign, materialize a panel, read a new outcome, or
open Model Construction.

## Exact identity and reuse

Reuse is allowed only when all identity dimensions match exactly:

- ordered source logical fingerprints and contract versions;
- stable-Universe fingerprint;
- knowledge-time cutoff;
- session-partition fingerprint;
- calculation-code SHA-256;
- parameter fingerprint; and
- upstream reusable-artifact fingerprints.

A mismatch creates a new immutable version. It never mutates or silently
aliases the existing artifact. The descriptor binds that logical identity to
the physical content SHA-256, row count, and optional session bounds.

## Custody boundary

Population, market-state, and feature-matrix families are outcome-blind.
Nuisance controls and outcome labels are outcome-bearing and may expose rows
only inside a newly preregistered Development screen and its independent
replay/red-team stage. Hypothesis intake, deduplication, data admission,
outcome-blind qualification, and protocol design receive no label rows.

Ordinary agent work should consume compact summaries. Row-level inspection
requires a named investigation and the stage permission defined here.

## Current implementation state

The registry is `contract_ready_not_materialized`: five family policies and
the exact content-identity type are implemented and tested, but the retained
artifact count is zero. No `/data` write, cleanup, deletion, new database,
service, parallel worker, campaign registration, or outcome access is granted.

The next bounded action is to define the point-in-time market-state vector and
then materialize only the exact population/market-state inputs required by its
outcome-blind qualification. Parallelism remains profile-first and must
preserve deterministic ordering.

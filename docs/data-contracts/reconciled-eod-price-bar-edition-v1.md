# Reconciled EOD Price Bar Edition V1

## Purpose

This contract defines a complete, immutable, explicitly selected research EOD
edition rebuilt from source custody under one frozen provider-mapping rule. It
does not overwrite or implicitly supersede canonical EOD Price Bar V1.

## Status

Design accepted; persistence and reader implementation pending.

## Identity

An edition is keyed by an immutable `edition_id`. A research input must bind
both that ID and the completed interval-manifest fingerprint. A directory name
or latest filesystem entry is not authority.

## Session grain

One session partition contains the complete accepted EOD Price Bar V1
cross-section for one XNYS session and one edition. The Parquet row schema is
the existing EOD Price Bar V1 Arrow schema.

## Required session bindings

Each session manifest records:

- edition ID and edition contract version;
- session date and provider;
- mapper policy ID and implementation revision;
- Grouped Daily source-package manifest and content fingerprints;
- source provenance: retained original or later reacquisition;
- source observation time;
- canonical Identity snapshot date and fingerprint;
- exact Identity-source logical fingerprint;
- rebuilt row count and content fingerprint;
- EOD V1 base row count and fingerprint;
- added, absent, economically changed, and unchanged key counts;
- quality counts, warnings, and reconciliation disposition; and
- Parquet filename/hash and completion status.

Fingerprints and relative logical paths are evidence. Credentials, headers,
raw response bodies, home paths, and secret locations are forbidden.

## Reconciliation rules

The business key is the EOD Price Bar V1 key. Comparison distinguishes:

1. keys present only in the rebuilt edition;
2. keys present only in EOD V1;
3. shared keys with changed economic fields;
4. shared keys with only declared provenance-time differences; and
5. fully unchanged keys.

ADR 0203 permits the expected repair class to add a previously omitted resolved
bar. It does not permit silent removals or economic changes. Any other diff
requires a typed quarantine reason and a separate decision before the session
can enter a completed edition.

## Interval completion

The interval manifest is written last and includes:

- exact evaluation and warm-up bounds;
- exact ordered session set and count;
- every session manifest fingerprint;
- total reconciliation counts by disposition and provenance;
- source-gap and quarantine counts, which must be zero for completion;
- frozen mapper policy and implementation revisions; and
- one deterministic logical fingerprint.

Readers reject an absent, partial, inconsistent, symlinked, or fingerprint-
mismatched interval manifest. They never infer completion from the number of
session directories.

## Authority

A completed edition is still only a candidate research price family. It gains
no Candidate, Production, Dashboard, publication, or model authority without
the later Historical Coverage and research-admission decisions.

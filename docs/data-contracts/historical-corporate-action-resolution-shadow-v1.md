# Historical Corporate Action Resolution Shadow V1

Contracts: `historical-corporate-action-resolution-shadow/1.0` and backward-
compatible `historical-corporate-action-resolution-shadow/1.1`.

This contract governs a disconnected, owner-only mapping of formally retained
Massive split/dividend source observations to exact event-date canonical
Identity Resolver records. It is not canonical Corporate Action, an Adjustment
Ledger, or a research-ready dataset.

## Inputs

The shadow binds:

- one complete split source package and one complete dividend source package
  for the same inclusive date range;
- both source manifest physical hashes and logical fingerprints; and
- one already-published `point_in_time_identity` family-evidence manifest for
  contract 1.0, or one or more such manifests for contract 1.1, each including
  its physical and logical identity.

Contract 1.1 permits overlapping evidence only when the complete artifact
binding for every overlapping session is identical. Every evidence session
must fall within the source range. The manifest records every evidence
binding, the combined first/last session, unique session count, overlap count,
and literal zero overlap conflicts. Source dates outside the combined exact-
session set remain quarantined; coverage is never filled by inference.

For every source event date present in the Identity evidence, the builder
verifies the exact snapshot completion manifest and Resolver manifest/Parquet
against the evidence references. Resolver schema, content fingerprint,
provider, date, count, ticker uniqueness, and stable-ID types must pass.

## Resolution policy

- Resolution uses only the provider ticker from the exact event-date Resolver.
- No latest, nearest-session, name, ticker-pattern, or current-Universe fallback
  exists.
- A missing exact Identity session is quarantined with
  `event_date_identity_unavailable`.
- A ticker absent from an available exact-date Resolver is quarantined with
  `unresolved_ticker`.
- Any source row that the typed mapper cannot represent stops the build; no row
  may be silently dropped.
- Output is one-to-one with source rows and retains each source page's actual WH
  Alpha observation time.

The first isolated shadow uses local observation revision `1`. This is not a
claim about the provider's historical revision number. Repeat acquisition and
append-only revision diff must be designed before canonical promotion.

## Physical output

The owner-only output tree contains:

- `shadow.json` under contract `1.0`; and
- one existing provider-neutral Corporate Action Source Observation 1.1
  Parquet partition per nonempty event year, each with its own manifest.

Contract 1.0 retains its original `/tmp` boundary. Contract 1.1 may also use
one explicitly supplied owner-only persistent Dell candidate root. The output
must be a direct child of that exact real mode-0700 root; broader, nested,
symlinked, or mode-drifted paths fail closed. Storage location grants no
canonical authority.

Every directory is mode `0700`; every completed file is mode `0400`. Formal
reread requires the exact file/directory set, business-key uniqueness,
physical hashes, logical fingerprints, record counts, year partitions,
observation semantics, and aggregate counts.

## Manifest summaries

The manifest records source and Identity evidence identities, source/mapped
counts, exact-date availability counts, resolution/record/action/quality-flag
counts, output artifact identities, and the aggregate fingerprint of every
used exact-date Resolver binding.

It also fixes the following values at zero:

- external requests;
- canonical data writes;
- Adjustment Ledger writes;
- analytics executions;
- publications;
- deployments; and
- scheduler changes.

All output remains `outcome_reconciliation_only`. Even a resolved stable ID is
not evidence that the action was knowable before the historical signal date.

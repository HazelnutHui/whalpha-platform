# Bounded Identity Extension Family Evidence

Use this workflow only to publish a reviewed, explicit set of already
canonical Identity snapshots as one immutable evidence object. It is not an
Identity fetch, Identity Apply, EOD update or Historical Coverage operation.

## Build a no-write plan

Run the project Python wrapper with
`tip_api.services.historical_family_evidence_publication_plan_cli` and the
`build-identity-extension` command. Supply the approved Dell data root, repeat
`--session YYYY-MM-DD` for every exact session, and supply a new direct
`/tmp/*.json` plan path.

Expected output includes:

- the Identity-only contract and operation;
- the exact first, last and total sessions;
- one family and one absent target;
- evidence and plan fingerprints;
- zero external requests and zero canonical writes; and
- false Historical Coverage, research and performance authority.

Use `verify-identity-extension` with the exact plan SHA-256 to formally reread
the plan and every bound source byte. Do not continue if any source, target,
mode, owner, path, hash, count or fingerprint differs.

## Apply an exactly reviewed plan

Run `tip_api.services.historical_family_evidence_apply_cli` with
`--source-scope identity-extension`, the exact plan path and all three reviewed
fingerprints. Apply may create only the one absent evidence target beneath the
approved Dell data root. It must report one formal reread, zero external
requests, zero overwritten partitions and zero deleted partitions.

Use `--verify-then-complete` only after an interrupted Apply left the exact
target complete, or to prove that a completed target is unchanged. A recovery
request with no completed target is deliberately rejected.

## Post-Apply checks

1. Confirm the published family is only `point_in_time_identity`.
2. Confirm the outside-inventory fingerprints match.
3. Confirm the target contains only `manifest.json` and formally rereads.
4. Preserve the reviewed plan and compact Apply result in the dated audit.
5. Build a new-version corporate-action resolution shadow; never overwrite an
   earlier shadow or infer that the evidence itself resolved an action.

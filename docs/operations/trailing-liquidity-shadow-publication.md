# Trailing Liquidity Shadow Publication Runbook

## Boundary

This is an offline derived-data operation. It must not access provider credentials, Massive, SEC, OCI, Git remotes, or any other network service. It does not update production Universe membership or Dashboard assets.

## Preflight

1. Require the approved host, repository branch/HEAD, and clean worktree.
2. Validate expected and actual latest XNYS sessions and require freshness lag zero.
3. Reread the completed 20-session descriptor, all EOD partitions, physical hashes, and same-day identity references.
4. Reread Provider-Classified membership evidence and compare the approved descriptor and Candidate A/B audit fingerprints.
5. Require all publication targets and staging paths to be absent for a first publication.
6. Run offline focused and full regression tests under the socket guard.

## Commands

The entrypoint defaults to dry-run:

```bash
scripts/admin/publish-trailing-liquidity-shadow.sh \
  --analysis-session YYYY-MM-DD \
  --membership-evidence-as-of-date YYYY-MM-DD \
  --expected-descriptor-fingerprint SHA256 \
  --expected-candidate-a-fingerprint SHA256 \
  --expected-candidate-b-fingerprint SHA256 \
  --calculated-at YYYY-MM-DDTHH:MM:SSZ \
  --data-root /absolute/approved/root
```

Only a separately approved production execution adds `--apply`. A failed apply is not retried in the same operation.

## Postflight

Reread both Parquet datasets and the logical marker through the formal repository. Reconcile A/B primary reasons, validate physical hashes and source references, require staging residue zero, and prove canonical protected inventory unchanged. Do not generate Dashboard assets or activate a Universe.

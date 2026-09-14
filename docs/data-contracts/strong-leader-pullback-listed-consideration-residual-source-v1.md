# Strong-Leader Pullback Listed-Consideration Residual Source V1

## Purpose

`strong-leader-pullback-listed-consideration-residual-source/1.0` retains the
single official SEC document authorized by the three-case residual source plan.
It is source custody only and does not interpret document content.

## Binding and limits

The package binds the exact residual plan report and decision fingerprint. Its
only request is sequence 174, the frozen Fifth Third CIK, accession, primary
document URL, target stable ID, and proposed consideration stable ID.

The acquisition reuses the established SEC transport and artifact contract:

- at most two requests per second and three retries;
- at most 64 MiB of retained source content;
- exact response URL, content type, byte count and SHA-256 reconciliation;
- atomic per-document checkpointing and formal rehash on resume;
- owner-only `0700/0400` custody; and
- completed-partial adoption only after full plan and artifact reread.

The manifest records plan hashes, implementation revision, observation and
completion time, request/retry counts, byte count, content type, and artifact
fingerprint. Exact completed reruns perform zero network requests.

## Authority

The package retains no credential material and grants no identity or terminal-
value authority. It creates no outcome, label, return, metric, canonical data
or Historical Coverage write, research admission, Candidate write,
publication, deployment, or scheduler change.

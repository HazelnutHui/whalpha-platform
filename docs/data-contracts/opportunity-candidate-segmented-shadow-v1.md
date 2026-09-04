# Opportunity Candidate Segmented Shadow V1

## Status and purpose

`opportunity-candidate-segmented-shadow/1.0` is an offline Dell-local proof of
lossless session segmentation for a completed Candidate Audit V1. It is not a
Candidate score contract, active daily input, publication, Snapshot source, or
performance result.

## Source boundary

Creation requires one fully validated Candidate Audit 1.0 or 1.1. The shadow
manifest freezes:

- source manifest SHA-256 and Candidate audit logical fingerprint;
- source schema, execution mode, as-of session, Universe order, calculation
  versions, parameter-set IDs, and parameter fingerprints;
- ordered Candidate sessions and one descriptor per session;
- the eight schema-neutral V1 business projection fingerprints;
- current Oracle fingerprint, zero mismatch, raw-fact/permutation gates, and
  every source equivalence flag; and
- the exact parameter, warning, and optional incremental-validation evidence
  needed to reconstruct the source business projections.

The source path is physical run evidence and is not a stable logical identity.

## Session segment

Each `segments/session=YYYY-MM-DD.json` contains exactly one Candidate session:

- the source panel;
- two ordered Universe Candidate batches;
- all ordered Candidate state and transition rows for that session;
- raw-fact and cross-section-normalization rows for that session;
- the six current risk-mode results only for the shadow as-of session; and
- the current Oracle record only for the shadow as-of session.

Every payload binds the shadow contract, source audit identity, session,
Universe order, record counts, and a canonical logical fingerprint. The root
manifest descriptor binds the relative path, byte count, SHA-256, logical
fingerprint, and all record counts.

V1 raw facts use a deterministic whole-history canonical ordering that is not
necessarily session-major. Each segment therefore also retains the exact V1
source ordinal aligned to every raw-fact row. Formal reconstruction restores
that order before comparing the V1 business fingerprint; it never weakens the
comparison to an unordered set.

## Custody and validation

- Output is a new owner-controlled direct child of `/tmp`.
- Root and `segments` directories are mode `0700`; completed files are mode
  `0400`; symlinks and unexpected files fail closed.
- JSON is UTF-8, NFC-normalized, key-sorted, compact, ASCII-escaped, and ends
  with one newline.
- The completion manifest is written last in a private staging directory; the
  complete directory is atomically renamed to the final path.
- Formal reread rechecks canonical bytes, exact file set, descriptors, typed
  Candidate/state/risk fingerprints, session order, current-only Oracle/risk
  scope, and all eight reconstructed V1 business fingerprints.

The bounded current-checkpoint reader still hashes every declared segment and
checks the complete file set, but parses typed business records only from the
latest segment. It is future append-input evidence, not a substitute for the
periodic full semantic reconstruction.

## Explicit non-authority

The shadow cannot feed daily planning, MI, Snapshot, bundle, deployment, UI,
research performance, or Production. It does not authorize `/data` writes or a
new scheduler action. Cutover requires a later ADR after real multi-session
append, cold comparison, crash recovery, retention, and downstream compatibility
have all passed.

## Real Dell proof

The 2026-09-03 V1 audit produced ten segments and reconstructed all eight
business projection fingerprints exactly. The complete one-time conversion
and reread took 548.57 seconds and 11,008,352 KiB peak RSS. The bounded current
reader rehashed every segment while parsing only the latest one in 16.53
seconds and 855,712 KiB peak RSS. It returned two Candidate batches, 3,549
current state rows, and six current risk results. These measurements establish
the storage/read boundary only; no daily append or cutover claim follows.

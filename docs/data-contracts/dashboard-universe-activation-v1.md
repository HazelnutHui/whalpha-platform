# Dashboard Universe Activation V1

Dashboard Universe Activation V1 is the completed production policy boundary between reviewed shadow membership and Dashboard analytics.

The activation dataset contains exactly two frozen records with stable IDs, display metadata, default status, member count, provider-type composition, membership fingerprint, upstream fingerprints, current/previous EOD fingerprints, limitations, and a verifiable Legacy rollback reference. The logical manifest records the 20-session window, reviewed override count, activation catalog, source review fingerprint, and Legacy count/fingerprint.

Publication uses explicit Arrow schema, deterministic row ordering and content fingerprints, physical Parquet SHA-256, same-filesystem staging, atomic rename, and a logical marker written last. Existing, partial, conflicting, symlinked, or path-escaping targets fail closed. A formal reader revalidates the activation and its pre-activation review before exposing member IDs.

The administrator CLI defaults to dry-run. `--apply` is the only write mode; unknown or extra arguments exit 2. A successful apply must complete a final production-root reread and exit 0.

This contract activates Dashboard selection only. It does not claim verified issuer domicile, alter canonical inputs, or make Legacy a normal user option.

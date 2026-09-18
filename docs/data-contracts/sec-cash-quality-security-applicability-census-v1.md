# SEC Cash-Quality Security Applicability Census V1

This aggregate census asks whether each issuer-level TTM observation has enough
point-in-time evidence to enter a later listed-security projection stage. It
does not create projected values or security-level financial rows.

The input plan binds the TTM package, its source-occurrence lineage, the exact
daily filer/security link partitions needed by recovered signal sessions, the
provider-form snapshot, and the offline XNYS calendar version. Signal sessions
must come from retained component lineage; fiscal labels, filing dates, and
calendar guesses are forbidden substitutes.

The census separately counts same-session CIK linkage, all linked securities,
common-security cardinality, source knowledge by signal open, stable IDs,
ticker changes, provider-observed common/ADR forms, effective-date gaps,
listing-interval gaps, and issuer-structure gaps. SEC filer identity is never
treated as listed-security proof. Unknown, late, retrospective, ambiguous, or
multi-common evidence remains quarantined.

The owner-only closed set contains canonical plan, result, and forward/reverse
verification JSON. Fully applicable coverage must remain zero unless every
independent gate is proven. All projection, factor, outcome, Validation,
Holdout, Candidate, Product, and Production authority fields are false. See
[ADR 0308](../decisions/0308-census-listed-security-applicability-before-cash-quality-projection.md).

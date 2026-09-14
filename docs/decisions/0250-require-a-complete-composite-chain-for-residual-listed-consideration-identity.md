# ADR 0250: Require a Complete Composite Chain for Residual Listed-Consideration Identity

## Status

Accepted.

## Context

Nine listed merger-consideration identities passed the original four-element
registration-document gate. Two other registration documents prove the same
transaction and share classes but contain a variable-ratio formula rather than
the final ratio. One originally selected filing was an unrelated notes
offering, but the exact merger 424B3 is now in private custody.

The target companies' retained completion 8-K disclosures independently state
the final ratios and both security classes for all three residual cases. A
name, ticker, formula-derived guess, or completion disclosure alone is still
insufficient to assign the listed consideration security.

## Decision

Adjudicate only the three frozen residual cases. For the two variable-formula
cases, require the issuer registration to prove the transaction, target common
security, and consideration common-security class, and require the target
completion disclosure to prove the exact final ratio and both security terms.

For Fifth Third/Comerica, require the replacement registration document itself
to prove the transaction, both common-security classes, and exact ratio, with
the completion disclosure providing an independent cross-check. In every case,
also require the frozen CIK-to-point-in-time stable common-security chain and
all plan, artifact, document, and prior-decision fingerprints to agree.

An incomplete or changed chain remains unassigned. Preserve the original nine
decisions rather than rewriting their historical report.

## Consequences

The residual report can add at most three evidence-scoped stable-security
assignments and exposes both the residual and cumulative counts. It does not
calculate a terminal value, create a strategy outcome or return, write `/data`
or Historical Coverage, admit research, publish, deploy, or change a scheduler.

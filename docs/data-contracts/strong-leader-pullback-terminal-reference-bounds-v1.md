# Strong-Leader Pullback Terminal Reference Bounds V1

`strong-leader-pullback-terminal-reference-bounds/1.0` aggregates the fixed
18-security / 88-path residual terminal population without reading an outcome.
It binds every case to stable `instrument_id`, prior gap state, crossing-path
count, bound state, gross USD reference interval, evidence fingerprints, and
any still-missing source role.

The only states are:

- `exact_reference_ready`, restricted to the official-timetable-backed last
  U.S. close policy;
- `finite_interval_ready`, with lower gross value zero and a finite evidenced
  upper value; and
- `source_evidence_pending`, with no policy, value, or implied estimate.

Allowed interval policies are fixed cash, cash plus aggregate CVR cap, maximum
listed consideration, and source-valued unlisted consideration. Evidence may
bind retained payoff terms, retained SEC content, or canonical target/successor
closes. Evidence locators must be unique and deterministically ordered.

The report reconciles 18 cases and 88 paths to the prior 214 exact-reference
paths and the immutable 302-path terminal population. It rejects count drift,
unordered or duplicate cases, malformed values, nonzero interval floors,
pending cases with values, ready cases without evidence, and any fingerprint
change.

Conversion to Research Admission V2 reports exact, interval, and unbounded
paths separately. The contract contains zero outcome, performance, parameter
selection, external request, canonical write, or Production authority. A
complete bounds report still does not itself create a return label; it only
satisfies one input gate for reconstructed development admission.

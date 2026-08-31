# Quant Research Statistics Adversarial Audit — 2026-08-31

## Scope

Repository-only synthetic audit of Candidate Strategy Research Statistics 1.0.
It used no provider, credential, network, canonical history or `/data` path.

## Evidence

| Scenario | Required behavior | Observed behavior |
| --- | --- | --- |
| Stable positive contrast | Fixture gates may pass but grant no authority | Passed; transition and performance authority remained false |
| Null validation contrast | Must not open holdout | Validation failed |
| Negative validation reversal | Must not open holdout | Validation failed |
| One-session crowding | Must remain inconclusive | Failed 20-comparable-session floor |
| One extreme positive session | Must not rescue weak typical outcome | Net-median gate failed |
| Differentially missing signals | Must remain visible and block advancement | Coverage reason emitted; complete-family validation gate failed |
| Cross-split outcome input | Must fail closed | Rejected before calculation |
| Unlocked holdout combination | Must fail closed | Rejected before calculation |
| Failed-validation holdout access | Must fail closed | Rejected before holdout calculation |

The independent descriptive Oracle reproduced every field across all 72
development summaries in the stable fixture. Exact constant-series bootstrap
expectations and adversarial behavior were verified separately; the Oracle does
not duplicate the primary pseudorandom bootstrap implementation.

## Result

The fixture mechanics pass this bounded audit after adding the complete cohort-
outcome coverage gate. This is not evidence that the research hypothesis works.
It proves only that the current synthetic execution rejects the registered
failure patterns. At this audit boundary, durable one-use holdout custody and a
formal independent inferential Oracle remained unimplemented; ADRs 0107 and
0108 subsequently add both controls using fixture-only evidence.

# Strong-Leader Pullback Terminal Reference SEC Source

This operation freezes and optionally retains the five free official SEC
documents required by ADR 0269. Planning is network-disabled and does not read
the private SEC User-Agent. Acquisition is a separate live operation and is
not authorized by this runbook.

The `20260915-v1` batch was acquired and formally reread on 2026-09-15. It is
immutable partial evidence: eight of eleven preregistered fields matched, but
the selected REVG and SKX files omit three required terms. Do not edit or
replace the retained package; use a separately frozen supplemental plan.

## 1. Publish the zero-request plan

Run only from a clean committed Dell source tree:

```bash
scripts/admin/plan-strong-leader-pullback-terminal-reference-sec-source.sh \
  --submissions-package /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions/snapshot=2026-09-10 \
  --submissions-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-plan/plan=20260915-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-plan \
  --planned-at <reviewed-UTC-timestamp> \
  --execute
```

The command formally rereads the retained Submissions archive and requires the
exact five CIK/accession/form/time/primary-document tuples. It atomically writes
one owner-only immutable report and reports zero external requests and zero
credential reads.

## 2. Acquire the five documents

This step requires separate explicit authorization and an already provisioned
private SEC User-Agent:

```bash
scripts/admin/acquire-strong-leader-pullback-terminal-reference-sec-source.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-plan/plan=20260915-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-plan \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-document-content/source=20260915-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-document-content \
  --execute
```

The live command loads the private User-Agent only after clean-repository and
plan checks. It permits only the five HTTPS SEC URLs, runs at no more than two
requests per second, allows at most two bounded retries per document, caps each
response at 64 MiB, validates URL/content type/bytes/hash, and writes an atomic
owner-only source package. It never serializes the User-Agent.

Failure removes only the precisely owned partial directory. Do not manually
delete, edit, replace, or merge a partial/completed package. Review the failure
before any retry.

## 3. Post-acquisition boundary

Source custody proves only that the exact response bytes were retained. It does
not prove the requested field, terminal value, outcome, or return. A separate
zero-network adjudication must bind the five named facts, rebuild all 18 bounds,
and rerun Research Admission V2. No `/data`, Snapshot, publication, deployment,
scheduler, Candidate, validation, or holdout action belongs to this operation.

The initial review identified exactly two supplemental free SEC documents as
the minimal correction. Their metadata and frozen plan are recorded in the dated
[source review](../audits/strong-leader-pullback-terminal-reference-sec-source-2026-09-15.md).

## 4. Supplemental plan

The zero-network supplemental plan is retained at
`historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan/plan=20260915-v1`.
It allows exactly one REVG document and one SKX document. Reproduce its formal
reread from a clean tree with:

```bash
scripts/admin/plan-strong-leader-pullback-terminal-reference-sec-supplement.sh \
  --submissions-package /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions/snapshot=2026-09-10 \
  --submissions-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan/plan=20260915-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan \
  --planned-at 2026-09-15T02:14:15Z \
  --execute
```

The separately authorized `20260915-v1` supplement is now retained. Its exact
replay command is:

```bash
scripts/admin/acquire-strong-leader-pullback-terminal-reference-sec-supplement.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan/plan=20260915-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-supplement-content/source=20260915-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-supplement-content \
  --execute
```

This command cannot fetch a third URL and inherits the same SEC rate, retry,
size, hash, atomic-custody, and no-credential-retention boundaries as the
initial source operation.

The dedicated supplemental adjudicator reads only the retained two-file source
and tests the two REVG consideration fields plus the SKX mixed-election cash
field. Its contract contains no terminal reference, outcome, metric, parameter,
canonical-write, or Production authority.

## 5. Final zero-network terminal-reference review

Run only from a clean committed Dell source tree. This operation rereads the
V3/V4 terminal population, retained payoff evidence, the original and both
terminal SEC source packages, and six registered canonical EOD sessions. It
does not make a network request or read a forward outcome.

```bash
scripts/admin/review-strong-leader-pullback-terminal-references.sh \
  --gap-v3 /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v3/census=20260914-v3 \
  --gap-v3-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v3 \
  --gap-v4 /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v4/census=20260914-v4 \
  --gap-v4-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v4 \
  --payoff-terms /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms/adjudication=20260914-v1 \
  --payoff-terms-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms \
  --consideration /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-consideration-adjudication/adjudication=20260913-v1 \
  --consideration-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-consideration-adjudication \
  --legacy-sec-source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content/source=20260913-v1 \
  --legacy-sec-source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content \
  --terminal-sec-plan /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-plan/plan=20260915-v1 \
  --terminal-sec-plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-plan \
  --terminal-sec-source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-document-content/source=20260915-v1 \
  --terminal-sec-source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-document-content \
  --supplement-plan /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan/plan=20260915-v1 \
  --supplement-plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-sec-supplement-plan \
  --supplement-source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-supplement-content/source=20260915-v1 \
  --supplement-source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-reference-sec-supplement-content \
  --canonical-eod-root /data/trading-intelligence-platform \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-final-review/review=20260915-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-reference-final-review \
  --evaluated-at <reviewed-UTC-timestamp> \
  --execute
```

The report is an immutable source-derived boundary artifact. A complete result
must reconcile 18 cases / 88 residual paths, 219 exact paths, 83 finite-interval
paths, and zero unbounded paths. It still contains zero outcomes, metrics,
parameters, canonical writes, or Production authority. Research Admission V2
must be run separately; a bounds report alone does not open development.

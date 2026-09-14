# ADR 0251: Extend Listed-Consideration Reference Values without Rewriting Prior Evidence

## Status

Accepted.

## Context

The original terminal-reference report values nine strict listed-consideration
identities and retains three exclusions. A separate residual adjudication now
assigns those three identities from complete composite evidence. Rewriting the
prior report would obscure which evidence was available at each stage.

All three residual cases were already selected from the same matched daily
cessation population and use the same normalized payoff terms and canonical
EOD/Identity boundary as the original nine.

## Decision

Create an additive three-case reference-value report bound to both the original
nine-value report and the residual identity report. Reuse the same formula and
price gate:

`guaranteed cash + listed ratio × canonical unadjusted close`

Use the assigned consideration security's close on the target's first absent
exchange session. Require a unique valid USD latest-revision bar and preserve
the EOD/Identity integrity, custody time, source, revision, and quality flags.

Keep the original nine-value report immutable and expose prior, residual, and
cumulative counts explicitly.

## Consequences

The two reports together can document at most 12 daily gross reference values
without conflating evidence vintages. The extension is not an execution price,
legal settlement value, canonical terminal outcome, strategy label, return, or
option result. It writes no `/data` or Historical Coverage, admits no research,
and does not publish, deploy, or change a scheduler.

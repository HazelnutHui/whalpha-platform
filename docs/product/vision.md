# Product Vision

## Confirmed

Trading Intelligence Platform is a tool-oriented Trading Intelligence Dashboard. It should be conclusion-first and evidence-supported: the interface should quickly show what matters, then let the user inspect the supporting data.

The product supports human decision-making. It focuses on market structure rather than prediction. It should communicate clearly with professional terminology and avoid casual labels such as "seesaw" in the UI.

Price-derived metrics must not be mislabeled as actual capital flows. Relative performance, dollar volume, volume pressure, and price behavior can support useful estimates, but actual fund-flow claims require an appropriate source and methodology.

## Proposed

The first usable product should favor a clean dashboard with clear visual hierarchy, concise risk-regime language, and drill-down detail where useful.

## Deferred

Narrative explanation, richer event workflows, and AI-assisted interpretation are deferred until core data and dashboard behavior are reliable.

## Accepted Direction

The application stack is documented in [ADR 0005](../decisions/0005-application-technology-stack.md). React, TypeScript, Vite, and Apache ECharts are the accepted frontend and visualization direction. Production interaction details remain to be refined during scaffold and dashboard implementation.

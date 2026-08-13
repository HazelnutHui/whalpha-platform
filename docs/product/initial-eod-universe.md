# Initial EOD Universe

## Purpose

This document defines the accepted V1 universe boundaries for EOD market analysis. It records product-level universe semantics only. It does not create datasets, provider adapters, code, or physical schemas.

## Status

Accepted Boundary — Not Yet Implemented

## Market Structure Universe

Purpose:

- market structure analysis
- standard market heatmap / treemap
- sector breadth
- index and style strength
- large-cap contribution analysis
- stable daily comparison

Initial composition direction:

- S&P 500 constituents
- major market index ETFs
- sector ETFs
- style/factor ETFs

The Market Structure Universe is the stable analysis layer. It is not the complete stock-discovery scope.

## Dynamic Discovery Universe

Purpose:

- strong-stock discovery
- theme rotation
- unusual market changes
- broader opportunity discovery

Coverage direction:

- NYSE
- Nasdaq
- NYSE American
- common stock only

Exclusions:

- OTC
- warrants
- preferred stock
- funds
- SPAC units
- invalid or inactive securities

## Portfolio / Focus Override

Purpose:

- current holdings
- manually maintained watch lists
- deep research targets

Rules:

- Override membership preserves analysis eligibility even when Discovery filters fail.
- Override does not indicate bullishness.
- Override does not indicate a recommendation.
- Portfolio and Focus are different membership sources.
- Portfolio integration is not implemented in V1.
- Current Portfolio or Focus members must not be invented in documentation or code.

## Candidate Defaults

Dynamic Discovery Universe V1 Candidate Defaults:

- minimum price: USD 3
- minimum market capitalization: USD 300 million
- minimum 20-day average daily dollar volume: USD 5 million
- minimum trading history: 252 trading sessions
- recalculated after each EOD session

These values are Candidate Defaults, not permanent operating thresholds.

## Evaluation Required Before Locking Thresholds

Before the Candidate Defaults become stable operating rules, evaluate them against real data for:

- selected instrument count
- market-cap distribution
- sector/industry coverage
- daily membership stability
- excluded high-momentum names
- data availability and quality

## Point-in-Time Membership

Universe membership is point-in-time. Daily membership history must be retained. Current constituents must never be projected backward into history.

Missing critical inputs do not default to eligible. Missing inputs should produce exclusion or review reason codes.

## Non-Goals

- provider adapter implementation
- real universe evaluation
- live constituent data
- portfolio integration
- recommendation or signal generation
- fake ticker examples
- physical Parquet schema definition

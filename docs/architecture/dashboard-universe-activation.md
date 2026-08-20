# Dashboard Universe Activation Architecture

```text
Trailing Liquidity V1 + Reviewed Override V1
  -> Universe pre-activation review
  -> Dashboard Universe Activation V1
  -> one validated Universe selection
  -> Market Pulse / Breadth / Volume / Movers / Activity Map
  -> private multi-Universe snapshot
  -> authenticated React Dashboard
```

The completed activation reader is the only production membership entry point. It returns the catalog, sole default, immutable metadata, and stable `instrument_id` membership sets. Tickers are presentation only. All Dashboard modules are built from the same selected set; an unknown ID is rejected and source failures do not fall back to Legacy or demo.

The snapshot exporter calls the same overview service twice—once for each catalog ID—and binds both payloads to a versioned manifest with checksums. The frontend selects only catalog entries already present in that snapshot or API response. URL state stores a stable ID, is normalized to the default when invalid, and never becomes a path.

Legacy membership and historical releases remain intact for explicit operational rollback. They are not in the public-facing selector.

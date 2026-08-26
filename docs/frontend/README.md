# Frontend Documentation

The authenticated Dashboard has a persistent first-level workspace shell for
Market Structure & Activity (`市场结构与活跃度`) and Market Regime &
Opportunities (`市场风向与机会`). Universe, language, and protected Session
controls share the top utility header. The two
activated Universe views use stable URL selection. Market Regime & Opportunities
is the first item and default workspace; invalid Universe values normalize to
`Common Shares`, and API/Snapshot failures do not fall back to demo or Legacy.

This directory records frontend runtime boundaries and implemented local dashboard behavior.

- [Market Dashboard V1](market-dashboard-v1.md)
- [Market Regime & Opportunities](market-regime-opportunity-map-preview.md)
- [Dashboard Universe V1](../product/dashboard-universe-v1.md)
- [Private Dashboard Publication](../architecture/private-dashboard-publication.md)

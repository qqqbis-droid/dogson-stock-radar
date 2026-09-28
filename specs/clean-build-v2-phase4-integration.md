# Clean Build 2.0 — Phase 4 Integration Record

Status: `REAL-DATA PREVIEW / NOT PRODUCTION CUTOVER`

## Implemented
- Public v1.x market / close / intraday / daytrade JSON are read only through a Migration Adapter.
- Close, intraday and daytrade are emitted as separate mission datasets; the UI never reuses close conclusions as intraday/daytrade conclusions.
- Each output preserves `trade_date`, `as_of`, `known_at`, `build_id`, `freshness` and source provenance.
- Old or non-live intraday/daytrade snapshots are `CLOSE_FREEZE/FROZEN` and are never actionable.
- Old close snapshots are `STALE`, receive `DATA_QUALITY_RISK`, and are never actionable.
- Missing Entry Position cannot become a positive execution signal.
- Homepage downloads only 15 decision summaries; full index is lazy-loaded for search/filter/load-more; detail is lazy-loaded on click.
- Public preview intentionally emits an empty portfolio dataset. Private holdings must never be committed to the public repository.

## Still Shadow
- Stage Confidence weights / expiry.
- Opportunity Ranking within-bucket predictive weights.
- Final Chip / Sector / Technical calibration.
- Dynamic Cluster / concentration in core score.

## Cutover rule
This phase makes the website eligible for a real-data online Preview. It does not authorize replacing production `main`. Phase 5 Shadow and rollback acceptance are still required before Phase 6 production cutover.

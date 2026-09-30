# Clean Build 2.0 — Implementation Readiness

## Phase status
- Phase 0 Contract: implemented and CI-gated.
- Phase 1 Data: atomic demo bundle + manifest + validation scaffold implemented.
- Phase 2 Engine: structural fail-closed bridge / action synthesizer implemented. Predictive thresholds remain Shadow.
- Phase 3 UI Skeleton: four-page mobile-first static preview implemented against the canonical bundle.
- Phase 4 Integration: **not yet promoted**. Real v1.x data must pass through the Migration Adapter and be compared with the old site.
- Phase 5 Shadow: requires 20–40 trading days for predictive rules/weights.
- Phase 6 Cutover: blocked until Shadow and rollback gates pass.

## What “ready to build the website” means
The new UI may now be developed on `clean-build-v2` because its data contract, bundle loader, single-state UI skeleton and fail-closed rules exist. It must not replace production `main` yet.

## Non-negotiable gates before production cutover
1. Real-data adapter produces one atomic 2.0 bundle with no mixed build/date.
2. Cross-view consistency tests pass.
3. Stale/fallback states never become actionable.
4. Shadow comparison has no unresolved P0/P1 divergence.
5. Rollback to existing production is tested.

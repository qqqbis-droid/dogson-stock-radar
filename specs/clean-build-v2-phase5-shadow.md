# Clean Build 2.0 — Phase 5 Shadow

Status: `STARTED / COLLECTION NOT COMPLETE`

## Online preview eligibility
Phases 0–4 are implemented sufficiently to publish the 2.0 branch as an **online Preview**. Production `main` remains unchanged.

The Preview reads only public market datasets through the Migration Adapter. Private holdings are intentionally excluded from the public repository and public Preview.

## Shadow collection
`v2-shadow.yml` fetches the latest public production datasets from `main`, builds a fresh Canonical 2.0 Atomic Bundle, runs contract/engine/bundle gates, records one report per distinct source build, and commits only validated public Preview data + Shadow reports to `clean-build-v2`.

The Shadow report tracks:
- source vs canonical row coverage,
- Lifecycle / Action / Bucket / Freshness distributions,
- fail-closed safety violations,
- source-date consistency,
- build lineage.

Duplicate source builds are not counted as additional trading-day samples.

## Production cutover remains blocked
Phase 6 cannot replace `/` until 20–40 distinct trading-day Shadow samples are collected and reviewed, predictive thresholds have versioned validation evidence, and rollback is verified.

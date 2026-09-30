# Clean Build 2.0 — Phase 5 Shadow

Status: `ACTIVE / AUTO-COLLECTING / PROMOTION NOT READY`

## Online preview eligibility
Phases 0–4 are implemented sufficiently to publish the 2.0 branch as an **online Preview**. Production `main` remains unchanged.

The Preview reads only public market datasets through the Migration Adapter. Private holdings are intentionally excluded from the public repository and public Preview.

## Shadow collection
`v2-shadow.yml` fetches the latest public production datasets from `main`, builds a fresh Canonical 2.0 Atomic Bundle, runs contract/engine/bundle gates, records one report per distinct source build, and commits only validated public Preview data + Shadow reports to `clean-build-v2`.

The workflow runs automatically on weekdays and can also be manually triggered through `.github/triggers/v2-shadow.trigger` without creating a push loop.

The Shadow report tracks:
- source vs canonical row coverage,
- Lifecycle / Action / Bucket / Freshness distributions,
- fail-closed safety violations,
- source-date consistency,
- build lineage,
- static startup payload size for each of the four views so Summary/Detail split regressions are visible.

Duplicate source builds and repeated runs from the same trading date are not counted as additional trading-day samples.

## Distinct-day progress source
`shadow/summary.json` is the canonical Phase 5 progress summary. It reports:
- distinct trading-day sample count,
- PASS / WARN / FAIL counts,
- unresolved safety violations,
- minimum observed coverage,
- current/max startup transfer sizes by view,
- remaining blockers before the 20-day minimum review window.

`shadow/latest.json` is the most recent detailed report. Historical reports are stored under `shadow/reports/`.

## Performance interpretation
Startup payload measurement is a structural transfer-size guard only. Browser first-interactive time and tap/open latency remain separate measured SLO gates and must not be inferred from byte size alone.

## Production cutover remains blocked
Phase 6 cannot replace `/` until 20–40 distinct trading-day Shadow samples are collected and reviewed, predictive thresholds have versioned validation evidence, unresolved P0/P1 divergence is zero, and rollback is verified.

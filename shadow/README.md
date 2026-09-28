# Clean Build 2.0 — Phase 5 Shadow Ledger

This directory stores **public-system** Shadow validation reports only. It must never contain the user's private portfolio, executions, account information, or other private data.

## Promotion rule
A predictive rule/weight may not move from `shadow` to `active` merely because the code runs. Promotion requires:

- 20–40 **distinct trading-day** reports,
- no unresolved P0/P1 data/semantic divergence,
- no `nonlive_actionable`, `failed_actionable`, mixed-build or future-leakage safety violation,
- stable coverage and cross-view consistency,
- a versioned validation report linked from `threshold_registry.json`.

Structural safety rules can remain Active while predictive thresholds/weights continue in Shadow.

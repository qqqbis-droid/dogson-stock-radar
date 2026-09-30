# Clean Build 2.0 — Phase 0 Freeze Record

Status: `IMPLEMENTATION CANDIDATE`

Phase 0 establishes the contract boundary before any 2.0 UI is connected to live data.

## Frozen
- Common envelope / time semantics
- Canonical enums
- Unknown / null semantics
- StockDecision ownership
- Market / Sector / TradePlan / TradeCase / Portfolio / Evidence / Zone / Delta schemas
- Atomic bundle manifest
- Threshold / taxonomy / version registries
- Contract CI gate

## Active vs Shadow
Structural safety rules are Active. Predictive thresholds and ranking weights without enough historical samples remain Shadow/Candidate and must not be presented as historically validated.

## Exit criteria
Phase 0 is considered passed only when the `Clean Build 2.0 Contract Gate` workflow is green on `clean-build-v2`.

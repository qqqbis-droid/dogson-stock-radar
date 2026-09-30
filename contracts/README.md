# 犬子老師・飆股雷達 Clean Build 2.0 — Contract Skeleton

本目錄是 Clean Build 2.0 的 Canonical Contract。UI、資料層與 Decision Engine 都必須遵守這裡的 schema / registry，不得自行猜欄位或硬編碼另一套規則。

## Phase 0 Freeze Gate
- Schema / enum / null semantics / versioning 已固定。
- Threshold / taxonomy 由 Registry 管理。
- Version Registry 是版本關係唯一真相來源；Atomic Bundle 必須綁定同一組 `version_set_id`，禁止 schema / engine / threshold / taxonomy 局部漂移。
- `build_id` 是不可變資料產物身分，不是 contract / engine 版本號；每日重建不得自行升版。
- Legacy v1.x 僅能經 Migration Adapter 進入 2.0。
- 未完成歷史驗證的數值模型標記為 `shadow`，不得直接升級為正式交易判斷。
- 所有 contract tests 必須通過後，才能進 Phase 1 Data。

## Canonical principles
1. `null != 0`
2. `UNKNOWN != NEUTRAL`
3. UI 只 render Canonical objects，不重算 Stage / Action / Ranking。
4. 同一畫面只能使用同一 `build_id`。
5. `as_of` 與 `known_at` 分離，禁止 future leakage。
6. fallback 不得提高 actionability。
7. ActualExecution 才能改變 PortfolioPosition。
8. Manifest 的版本欄位必須完整匹配 Version Registry 的 active version set；不允許 partial upgrade。

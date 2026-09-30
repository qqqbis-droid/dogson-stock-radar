# 犬子老師・飆股雷達 2.0 — Product Hardening Plan

- 啟動日期：2026-09-30
- 主工作分支：`clean-build-v2`
- 產品目標：讓使用者在 10 秒內知道「今天市場能不能做、資金在哪裡、先看哪幾檔」；30 秒內知道「為什麼值得看、要等什麼、哪裡失效」。
- 固定原則：分數代表條件同步程度，不代表上漲機率；市場環境分獨立；資料時間與證據優先於畫面完整。

## P0 — 先把核心做穩

### P0.1 三任務資料完整性與 freshness Gate
- [x] 盤中：`decision_intraday_detail`、`stock_detail_intraday`、`zone_intraday` 必須同一 Atomic Build。
- [x] 當沖：`decision_daytrade_detail`、`stock_detail_daytrade`、`zone_daytrade` 必須同一 Atomic Build。
- [x] 盤後：`decision_close_detail`、`stock_detail_close`、`zone_close` 已有 Evidence Gate。
- [x] LIVE 時段報價延遲超過門檻時，禁止標成即時；結構過舊時可保留報價但必須撤銷 actionable。
- [x] 5 分鐘報價時鐘與 10 分鐘結構時鐘分開顯示。

驗收：三個任務若「有分數但缺 Evidence/Zone」必須直接阻擋部署；任何 stale/unknown 不可顯示可執行。

### P0.2 前端單一寫入者 / Renderer 收斂
- [x] 不再新增 MutationObserver overlay 補丁。
- [x] 卡片由 `app.js` 單一 renderer 負責。
- [x] 詳情由 `stock-detail-renderer.js` 單一 renderer 負責。
- [x] 市場/資金由 `market-capital-renderer.js` 單一 renderer 負責。
- [x] 數字格式、tick、白話 copy 在 render 前完成，不再 render 後二次改 DOM。
- [x] `validate_single_writer_ui.py` 禁止舊 overlay 重新進入 production index。

驗收：同一資訊不重複、無閃跳、重複 render 不改變結果（idempotent）。

### P0.3 排名語意與 Shadow 標示
- [x] 盤後：候選層級 → 波段品質 → 進場位置 → 資料信心 → 代號。
- [x] UI 明確寫「注意力排序，不代表上漲機率」；卡片顯示「明日候選 #N」等 bucket 語意。
- [x] Shadow 樣本進度綁入 `radar_stats`，顯示實際樣本天數 / 20 日最低審查門檻 / 40 日目標窗。

驗收：`#1` 不再被誤解成勝率第一；未經 20–40 交易日驗證的權重不得標成已驗證模型。

## P1 — 補齊決策流程

### P1.1 頂部市場快訊列
- [x] 市場狀態、/15、加權、櫃買、更新狀態。

### P1.2 今日雷達摘要
- [x] 依任務顯示候選／觸發／剛啟動／回踩／風險等快速統計。

### P1.3 快速篩選
- [x] 階段、狀態、位置（靠支撐/突破/壓力近/過熱）、族群。

### P1.4 資金 drill-down
- [x] 族群 → 個股清單 → 完整個股；市場／資金與個股詳情使用同 Build 資料。
- [ ] 下一輪補：族群個股的排序理由與「該族群中為什麼先看這幾檔」摘要。

### P1.5 全市場搜尋與排名池分離
- [x] 官方全市場皆可搜尋。
- [x] 不進排名池者顯示「未排名」與原因，不產生假分數。

### P1.6 庫存私人層
- [ ] 實際成交持股（包含 1 股）。
- [ ] 進場理由 / 持有理由 / ✅⚠️❌ / 驗證條件 / 失效條件 / 策略。
- [ ] 私人資料不得 commit 到公開 repo。
- [ ] 優先採瀏覽器本機私人資料層或後續授權連接，不把持股寫入公共 Pages artifact。

## P2 — 體驗與驗證

- [ ] 深色模式。
- [ ] 更多市場資訊 / 資料來源 / Build / Contract / Shadow 驗證背景收合區。
- [ ] 手機互動 SLO：首屏、點卡、切分頁實測。
- [ ] Shadow 累積 20–40 個不同交易日後再校準排名與門檻。

## 部署／回歸保護

- [x] 盤後 Evidence Gate。
- [x] 盤中／當沖 Evidence Gate。
- [x] Single-writer UI Gate。
- [x] Close 排名實體順序與 `opportunity_rank` 強制一致。
- [ ] 最新 completed-session workflow 的 UI 驗證步驟全面換成 single-writer Gate（仍有舊檔 syntax check 要清除）。
- [ ] 正式 Pages artifact 增加產品級 smoke check：市場快訊、摘要、搜尋、資金 drill-down、個股詳情掛載點都必須存在。

## 不做的事

- 不再用新 V8/V9 overlay 去蓋前一層 bug。
- 不把盤後籌碼冒充盤中即時資料。
- 不用假資料補空結果。
- 不因 UI 要「看起來完整」而犧牲時間語意與證據一致性。
- 不把 Shadow/Candidate 權重包裝成已經證明有勝率優勢的模型。

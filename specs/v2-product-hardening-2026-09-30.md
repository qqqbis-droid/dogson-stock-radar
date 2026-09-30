# 犬子老師・飆股雷達 2.0 — Product Hardening Plan

- 啟動日期：2026-09-30
- 最近更新：2026-09-30 22:52（Asia/Taipei）
- 主工作分支：`clean-build-v2`
- 狀態：`FUNCTIONAL HARDENING COMPLETE / LIVE ACCEPTANCE PENDING`
- 產品目標：讓使用者在 10 秒內知道「今天市場能不能做、資金在哪裡、先看哪幾檔」；30 秒內知道「為什麼值得看、要等什麼、哪裡失效」。
- 固定原則：分數代表條件同步程度，不代表上漲機率；市場環境分獨立；資料時間與證據優先於畫面完整。

## P0 — 核心正確性與發布安全

### P0.1 三任務資料完整性與 freshness Gate
- [x] 盤中：`decision_intraday_detail`、`stock_detail_intraday`、`zone_intraday` 必須同一 Atomic Build。
- [x] 當沖：`decision_daytrade_detail`、`stock_detail_daytrade`、`zone_daytrade` 必須同一 Atomic Build。
- [x] 盤後：`decision_close_detail`、`stock_detail_close`、`zone_close` 必須同一 Atomic Build。
- [x] 非 LIVE 盤中／當沖不得保留 actionable。
- [x] LIVE 時段報價來源錯日或超過 freshness 上限會 fail closed。
- [x] 5 分鐘報價時鐘、最後真實成交、10 分鐘結構時鐘分開顯示。
- [ ] **下一個真實交易時段驗收**：09:00–13:30 實際量測 quote / structure / Pages publish latency，確認 GitHub cron 沒有再造成不可接受的延遲。

驗收原則：三個任務若「有分數但缺 Evidence / Zone / StockDetail」直接阻擋部署；任何 stale / unknown 不可顯示可執行。

### P0.2 前端單一寫入者 / Renderer 收斂
- [x] 不再新增 MutationObserver overlay 補丁。
- [x] 卡片由 `app.js` 單一 renderer 負責。
- [x] 市場／資金由 `market-capital-renderer.js` 單一 renderer 負責。
- [x] 族群內注意力排序由 `sector-ranking-panel.js` 擁有獨立 mount，不改寫市場 renderer 的 DOM。
- [x] 詳情由 `stock-detail-renderer.js` 單一 renderer 負責。
- [x] 庫存由 `portfolio-renderer.js` 單一 renderer 負責。
- [x] 數字格式、tick、白話 copy 在 render 前完成，不再 render 後二次改 DOM。
- [x] `validate_single_writer_ui.py` 禁止舊 overlay 重新進入 production index，並對所有 active JS 做 syntax check。

驗收：同一資訊不重複、無閃跳；舊 `market-capital-ui / detail-context / score-explain / card-display / ui-coherence / copy-polish` 不得重新掛回 production index。

### P0.3 排名語意與 Shadow 標示
- [x] 盤後：候選層級 → 波段品質 → 進場位置 → 資料信心 → 代號。
- [x] 盤中與當沖維持各自 mission 排名，不拿盤後分取代盤中執行排序。
- [x] UI 明確寫「注意力排序，不代表上漲機率」；卡片顯示 bucket / mission 語意。
- [x] Shadow 樣本進度綁入 `radar_stats`，顯示實際樣本天數 / 20 日最低審查門檻 / 40 日目標窗。

驗收：`#1` 不得被包裝成勝率第一；未經 20–40 交易日驗證的權重不得標成已驗證模型。

### P0.4 Product-level release smoke gate
- [x] 新增 `validate_product_surface.py`。
- [x] 共同 release validator 會連帶執行 product smoke，不再只做 JS syntax check。
- [x] 每次發布必查：市場快訊、三時鐘、雷達摘要、四種篩選、全市場搜尋、族群 drill-down、族群內先看、個股詳情、評分依據、私人庫存、Shadow 說明。

---

## P1 — 決策流程補齊

### P1.1 頂部市場快訊列
- [x] 市場狀態、/15、加權、櫃買、資料狀態。

### P1.2 今日雷達摘要
- [x] 依任務顯示候選／觸發／剛啟動／回踩／風險等快速統計。

### P1.3 快速篩選
- [x] 階段。
- [x] 狀態。
- [x] 位置：靠支撐／突破／壓力近／過熱。
- [x] 族群。

### P1.4 資金 drill-down
- [x] 族群 → 個股清單 → 完整個股；市場／資金與個股詳情使用同 Build 資料。
- [x] 新增「族群內先看」：只取該族群成分股中正式 mission ranking 的前 5 檔。
- [x] 顯示全雷達排名、mission 分數、進場位置、資料信心與 bucket。
- [x] 明確說明「不另外發明一套族群內分數」；缺完整執行分者不硬排名。

### P1.5 全市場搜尋與排名池分離
- [x] 官方全市場皆可搜尋。
- [x] 不進排名池者顯示「未排名／無完整執行分」，不產生假分數。
- [x] 官方 universe 與可排序雷達池分開顯示。
- [x] 若 upstream 沒保留 20 日成交金額等排除證據，就不假裝能精確說某檔一定因哪個條件被排除。

### P1.6 庫存私人層
- [x] 實際成交持股，包含 1 股。
- [x] 不記掛單／取消單。
- [x] 進場理由、持有理由、✅成立／⚠️弱化／❌失效、驗證條件、結構失效條件、策略、備註。
- [x] 私人持股只存在瀏覽器 `localStorage`，不得 commit 到公開 repo。
- [x] 與盤後 Atomic Build 結合顯示波段品質、支撐／壓力、估計損益與目前風險。
- [x] JSON 匯出／匯入備份。
- [x] 個股詳情可直接「加入／更新庫存」，仍統一寫入 `RadarPortfolioStore`。

### P1.7 個股詳情資訊層級
- [x] 第一層：狀態／動作／位置／支撐／壓力／Trigger／失效。
- [x] 第二層：為什麼值得看、分數組成與證據。
- [x] 第三層：資料品質、Build、模型／工程資訊。
- [x] 評分依據不搶第一屏。

---

## P2 — 體驗、觀測與驗證

### P2.1 深色模式
- [x] 淺色仍為預設。
- [x] 新增 browser-local 深色模式切換；theme controller 不改寫決策 DOM。

### P2.2 更多市場資訊／驗證背景
- [x] 排名規則。
- [x] 雷達池 vs 官方 universe。
- [x] Shadow / Candidate 語意與樣本進度。
- [x] 收合顯示 Active Build 與本機效能觀測。

### P2.3 本機瀏覽器互動觀測
- [x] 首個雷達 render 時間。
- [x] 個股詳情開啟 latency（median / P90）。
- [x] 手動更新到重新 render latency。
- [x] 僅存 `sessionStorage`，不把操作紀錄上傳。
- [ ] 收集足夠真實手機樣本後，才凍結首屏／點卡 SLO；目前不憑空設定漂亮門檻。

### P2.4 Shadow 校準
- [ ] 至少累積 20 個不同交易日後再進最低 review window；目標 40 日。
- [ ] predictive threshold / within-bucket weights 在完成驗證前保持 Candidate / Shadow。

---

## Conditional — 只有盤中驗收仍不夠快才啟用

### Direct quote API for visible stocks
- [ ] 現有 `/api/quote` 尚未接成 V2 production live source。
- [ ] 若下一個真實交易時段仍出現 GitHub cron 明顯 jitter，再改為對「目前可見／選定股票」直接 polling；報價時鐘與 10 分鐘結構時鐘仍要分開。
- [ ] 不為了顯示更快的數字而犧牲 MIS 真實成交時間語意。

---

## 部署／回歸保護

- [x] 盤後 Evidence Gate。
- [x] 盤中／當沖 Evidence Gate。
- [x] Single-writer UI Gate。
- [x] Active JS syntax Gate。
- [x] Product-level smoke Gate。
- [x] Close 排名實體順序與 `opportunity_rank` 強制一致。
- [x] 共同 `validate_market_capital_context.py` 會再呼叫 release-surface Gate，因此舊 workflow 自己的 syntax-check 清單即使尚未清乾淨，也不再是發布安全缺口。
- [ ] 維護性清理：`Latest Completed Session Refresh` 內仍可刪除已淘汰 overlay 的冗餘 `node --check`；此項不影響 production safety，排在功能驗收之後。

## 最新驗收

- Product Smoke Gate：PASS。
- Preview Gate：PASS。
- Phase 4 Real Data Preview：PASS。
- GitHub Pages Shadow Preview：PASS。
- `sector-ranking-panel` 最新 Pages Run：`36732099244` / #119 / SUCCESS。
- 前一輪 Pages artifact 已直接拆包驗證：`portfolio-store.js`、`portfolio-renderer.js`、`portfolio-quick-add.js`、`theme-toggle.js`、`runtime-observability.js`、`stock-detail-renderer.js`、`market-capital-renderer.js` 都實際存在於部署產物，且 `index.html` 真正載入。

---

## 現在真正剩下的事情

1. **下一個交易時段做 P0.1 真實盤中驗收**：quote age、structure age、Pages publish latency、畫面三時鐘。
2. **累積本機手機 latency 樣本**，再定義實測 SLO。
3. **累積 Shadow 至至少 20 個不同交易日**，再做 ranking / threshold calibration review。
4. 非阻塞維護：清掉 completed-session workflow 中已無作用的舊 overlay syntax checks。

除以上需要真實時間／樣本的項目外，本輪原始功能補強清單已完成並納入 release gate。未來若有 regression，應以 failing build/run 重新打開對應項目，不再用新的 V8/V9 overlay 疊補。

## 不做的事

- 不再用新 overlay 去蓋前一層 bug。
- 不把盤後籌碼冒充盤中即時資料。
- 不用假資料補空結果或排除理由。
- 不因 UI 要「看起來完整」而犧牲時間語意與證據一致性。
- 不把 Shadow/Candidate 權重包裝成已證明有勝率優勢的模型。

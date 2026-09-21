# 犬子老師・台股飆股雷達 Free Edition

這是 **0 元月費優先** 的 GitHub Pages 版本。

## 架構

- GitHub Pages：手機網頁
- GitHub Actions：排程抓資料並重新部署
- Yahoo Finance：日K / 5分K
- TWSE / TPEx：公司清單
- `localStorage`：手機上的「我的關注」

## 免費版限制

1. GitHub Actions 的 cron **不是即時排程保證**，尖峰時可能延遲。
2. 盤中不是券商逐筆行情。
3. 為了不把免費 Actions 用量炸掉，盤中只抓：
   - `config/watchlist.txt` 固定追蹤股票
   - 日K雷達前 150 名
4. 任意股票在「盤後」可查全市場；若它不在盤中活躍池，盤中頁會沒有5分K。
5. 目前不做 App 關閉後的 Web Push；打開網站即可看最新「剛啟動」。

## GitHub Pages 設定

Repository → Settings → Pages → Source 選 `GitHub Actions`。

第一次 push 到 `main` 後，到 Actions 手動執行一次 **Update Radar & Deploy Pages**。

## 個人固定盤中追蹤

編輯 `config/watchlist.txt`，一行一個股票代號。

目前預放：
2308、3711、2313、6223、3141、3661、3017、6669、6442、8046、3189、3037、6532。

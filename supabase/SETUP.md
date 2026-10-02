# INUKO LAB 雲端庫存設定

此目錄只放資料庫 schema 與公開前端設定說明。**禁止**把 Supabase `service_role`、資料庫密碼、券商帳密或任何私人憑證提交到 GitHub。

## 1. 建立 Supabase 專案

在自己的 Supabase 帳號建立一個專案。專案地區可選離台灣較近的區域。

## 2. 建立資料表與 RLS

在 Supabase SQL Editor 執行：

`supabase/migrations/20261002_0001_inuko_portfolio_cloud.sql`

它會建立：

- `inuko_brokerage_accounts`：主帳戶／第二帳戶
- `inuko_portfolio_ledgers`：每個帳戶的交易流水與持倉帳本
- `inuko_fee_profiles`：券商手續費／最低手續費／交易稅設定
- `inuko_portfolio_snapshots`：每日帳本快照
- RLS：每位登入者只能存取自己的資料
- `inuko_ensure_default_accounts()`：第一次登入自動建立「主帳戶」與「第二帳戶」

## 3. 設定 Magic Link 登入網址

Supabase → Authentication → URL Configuration：

- Site URL: `https://qqqbis-droid.github.io/dogson-stock-radar/v2/`
- Redirect URLs: 加入同一網址

若另有 preview/dev 網址，再逐一加入，不要使用不必要的廣泛 wildcard。

## 4. 填入公開瀏覽器連線值

Supabase Project Settings / API 取得：

- Project URL
- anon key 或 publishable key

填到：

`docs/v2/cloud-config.js`

```js
window.INUKO_CLOUD_CONFIG=Object.freeze({
  supabaseUrl:'https://YOUR_PROJECT.supabase.co',
  supabaseAnonKey:'YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY',
  version:'1.0.0'
});
```

這兩個值本來就是瀏覽器公開值；真正的資料隔離依賴 RLS。**不要**填 `service_role` key。

## 5. 驗收

1. 開啟「庫存」頁。
2. 應看到 `☁️ INUKO 雲端庫存`。
3. 輸入 Email，點「寄登入連結」。
4. 從 Email 點 Magic Link 回到網站。
5. 應自動建立「主帳戶」與「第二帳戶」。
6. 新增一筆測試成交，等待顯示 `☁️ 已同步`。
7. 登出、重新登入，測試成交仍能恢復。
8. 切換帳戶，兩個帳戶的庫存應彼此獨立。
9. 到 Supabase Table Editor 確認 `inuko_portfolio_snapshots` 有當日快照。

## 同步安全規則

- 雲端是登入後的主要來源；切換帳戶前先同步目前帳本。
- 每次寫入使用 `revision` 做樂觀鎖，避免另一台裝置的新版資料被舊版直接覆蓋。
- 若 revision 衝突，前端停止覆寫並先在本機保留衝突備份。
- 每次成功同步後，會 upsert 當日快照；同一天只保留最新版本。
- GitHub Pages 的部署與 UI 改版不會刪除 Supabase 中的帳本資料。

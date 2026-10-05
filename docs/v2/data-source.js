// Clean Build 2.0 data bridge.
// Prefer same-origin GitHub Pages data for iOS/Safari reliability.
// Keep raw.githubusercontent.com only as an emergency fallback for preview hosts
// that do not ship the validated data bundle locally.
(() => {
  const RAW_DATA_BASE = "https://raw.githubusercontent.com/qqqbis-droid/dogson-stock-radar/clean-build-v2/docs/v2/data/";
  const nativeFetch = window.fetch.bind(window);
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  function resolveDataFallback(input) {
    const value = typeof input === "string" ? input : input?.url;
    if (!value) return null;
    const marker = "./data/";
    if (!value.startsWith(marker)) return null;
    return `${RAW_DATA_BASE}${value.slice(marker.length)}`;
  }

  async function fetchRetry(input, options, tries = 3) {
    let lastError = null;
    for (let attempt = 0; attempt < tries; attempt++) {
      try {
        const response = await nativeFetch(input, options);
        if (response.ok) return response;
        lastError = new Error(`HTTP ${response.status}`);
      } catch (error) {
        lastError = error;
      }
      if (attempt < tries - 1) await sleep(500 * (attempt + 1));
    }
    throw lastError || new Error("資料讀取失敗");
  }

  window.fetch = async (input, init = {}) => {
    const remote = resolveDataFallback(input);
    if (!remote) return nativeFetch(input, init);

    const options = { ...init, cache: "no-store" };
    try {
      return await fetchRetry(input, options, 3);
    } catch (_) {
      return fetchRetry(remote, options, 2);
    }
  };

  function polishVisibleCopy() {
    const privacy = document.querySelector('.portfolio-privacy');
    if (privacy) privacy.textContent = '🔒 沒有登入時，資料只存在這台裝置。只記錄真的買到或賣掉的交易；沒成交或取消的委託不用記。';
    const footer = document.querySelector('footer');
    if (footer) footer.textContent = '分數只代表條件符合程度，不代表一定會上漲；排名只是注意順序。資料過期或不完整時，系統不提供操作建議。';
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', polishVisibleCopy, { once: true });
  else polishVisibleCopy();

  // INUKO is the product brand. Keep the legacy alias temporarily so older
  // browser add-ons do not break while they are being retired.
  window.__INUKO_DATA_FALLBACK_BASE__ = RAW_DATA_BASE;
  window.__DOGSON_DATA_FALLBACK_BASE__ = RAW_DATA_BASE;

  // V2 keeps Stage/Lifecycle and the legacy 60-minute technical lifecycle as
  // separate evidence layers. The detail add-on can fall back to the canonical
  // root hourly Engine so UI-only data preservation can never hide the 60K card.
  const h60=document.createElement("script");
  h60.src=`./hourly60-addon.js?v=20261002h60b`;
  h60.defer=true;
  document.head.appendChild(h60);

  // The post-close 60K screener is a separate mission mode. It reads the
  // canonical root hourly.json directly, rather than filtering only V2 Stage
  // candidates, so PRE_CROSS / EARLY / STABLE_CONT / ACCEL_CONT remain usable
  // as an independent full-market technical screen.
  const h60screen=document.createElement("script");
  h60screen.src=`./hourly60-screener.js?v=20261002h60screen2`;
  h60screen.defer=true;
  document.head.appendChild(h60screen);

  // Close Mission Integrity is a defensive display adapter. It never re-scores
  // stocks: it reconstructs quick-filter counts from the actual close decision
  // datasets when radar_stats is absent, and turns existing Zone/Engine evidence
  // into the missing blocker/upgrade/invalidation text.
  const closeIntegrity=document.createElement("script");
  closeIntegrity.src=`./close-mission-integrity.js?v=20261002closefix1`;
  closeIntegrity.defer=true;
  document.head.appendChild(closeIntegrity);

  // Portfolio Cloud is additive: until the public Supabase URL + publishable
  // key are configured it stays dormant and the current local ledger continues
  // to work. A service-role key must never be shipped to the browser.
  const cloudConfig=document.createElement("script");
  cloudConfig.src=`./cloud-config.js?v=20261005cloudsafe2`;
  cloudConfig.defer=true;
  cloudConfig.onload=()=>{
    const cloud=document.createElement("script");
    cloud.src=`./portfolio-cloud.js?v=20261002cloud1`;
    cloud.defer=true;
    cloud.onload=()=>{
      // Conflict resolution must never restore a stale local snapshot. This
      // safety layer snapshots the current local ledger before destructive
      // choices and syncs the latest local ledger at click time.
      const safety=document.createElement("script");
      safety.src=`./portfolio-cloud-safety-v2.js?v=20261005cloudsafe2`;
      safety.defer=true;
      document.head.appendChild(safety);

      const snapshots=document.createElement("script");
      snapshots.src=`./portfolio-snapshot-v1.js?v=20261002cloud1`;
      snapshots.defer=true;
      document.head.appendChild(snapshots);
    };
    document.head.appendChild(cloud);
  };
  document.head.appendChild(cloudConfig);

  // Brokerage statements estimate open-position P&L after the fees/tax that
  // would be charged if the position were sold now. Load this adapter after the
  // regular portfolio fee/store modules finish booting so their cloud/account
  // behavior stays unchanged while displayed costs and estimated P&L match the
  // broker-style whole-TWD charge convention.
  window.addEventListener('load',()=>{
    setTimeout(()=>{
      if(!document.getElementById('inukoBrokerMatchScript')){
        const broker=document.createElement('script');
        broker.id='inukoBrokerMatchScript';
        broker.src='./portfolio-broker-match.js?v=20261003broker1';
        document.head.appendChild(broker);
      }
      if(!document.getElementById('inukoPortfolioPriorityLadderScript')){
        const ladder=document.createElement('script');
        ladder.id='inukoPortfolioPriorityLadderScript';
        ladder.src='./portfolio-priority-ladder-v1.js?v=20261006srfix1';
        document.head.appendChild(ladder);
      }
    },0);
  },{once:true});
})();
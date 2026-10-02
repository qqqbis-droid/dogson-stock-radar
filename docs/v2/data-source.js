// Clean Build 2.0 data bridge.
// Prefer same-origin GitHub Pages data for iOS/Safari reliability.
// Keep raw.githubusercontent.com only as an emergency fallback for preview hosts
// that do not ship the validated data bundle locally.
(() => {
  const RAW_DATA_BASE = "https://raw.githubusercontent.com/qqqbis-droid/dogson-stock-radar/clean-build-v2/docs/v2/data/";
  const nativeFetch = window.fetch.bind(window);

  function resolveDataFallback(input) {
    const value = typeof input === "string" ? input : input?.url;
    if (!value) return null;
    const marker = "./data/";
    if (!value.startsWith(marker)) return null;
    return `${RAW_DATA_BASE}${value.slice(marker.length)}`;
  }

  window.fetch = async (input, init = {}) => {
    const remote = resolveDataFallback(input);
    if (!remote) return nativeFetch(input, init);

    const options = { ...init, cache: "no-store" };
    try {
      const local = await nativeFetch(input, options);
      if (local.ok) return local;
    } catch (_) {
      // Fall through to the remote validated public bundle.
    }
    return nativeFetch(remote, options);
  };

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
  h60screen.src=`./hourly60-screener.js?v=20261002h60screen1`;
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
})();
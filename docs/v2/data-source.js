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
  // separate evidence layers. Load the renderer add-on after this fetch bridge
  // is installed so it uses the same Atomic Build data path and fallback rules.
  const h60=document.createElement("script");
  h60.src=`./hourly60-addon.js?v=20261002h60a`;
  h60.defer=true;
  document.head.appendChild(h60);
})();
// Clean Build 2.0 Shadow data bridge.
// The UI shell can stay on a stable Vercel deployment while validated public
// market bundles continue to update on the clean-build-v2 branch.
(() => {
  const RAW_DATA_BASE = "https://raw.githubusercontent.com/qqqbis-droid/dogson-stock-radar/clean-build-v2/docs/v2/data/";
  const nativeFetch = window.fetch.bind(window);

  function resolveShadowData(input) {
    const value = typeof input === "string" ? input : input?.url;
    if (!value) return null;

    const marker = "./data/";
    if (!value.startsWith(marker)) return null;

    const relative = value.slice(marker.length);
    return `${RAW_DATA_BASE}${relative}`;
  }

  window.fetch = (input, init = {}) => {
    const remote = resolveShadowData(input);
    if (!remote) return nativeFetch(input, init);

    const options = { ...init, cache: "no-store" };
    return nativeFetch(remote, options);
  };

  window.__DOGSON_SHADOW_DATA_BASE__ = RAW_DATA_BASE;
})();

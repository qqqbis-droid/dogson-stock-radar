// v1.7.5 clean shell: one navigation owner + one dated status owner.
window.DOGSON_REALTIME_API = window.DOGSON_REALTIME_API || "";
window.DOGSON_UI_ASSET_VERSION = '1730';

// Data / scoring modules stay unchanged.
if (!document.getElementById('dogson-hourly-module')) {
  const s = document.createElement('script');
  s.id = 'dogson-hourly-module';
  s.src = './hourly.js?v=1530';
  s.async = true;
  document.head.appendChild(s);
}

if (!document.getElementById('dogson-decision-filters')) {
  const s = document.createElement('script');
  s.id = 'dogson-decision-filters';
  s.src = `./ui-filters.js?v=${window.DOGSON_UI_ASSET_VERSION}`;
  s.async = true;
  document.head.appendChild(s);
}

// UI reset: do not load the legacy nav / clean / stability / notice / status patch stack.
// v1750 creates a new visible header-status element instead of reusing legacy #status.
if (!document.getElementById('dogson-shell-v1750')) {
  const s = document.createElement('script');
  s.id = 'dogson-shell-v1750';
  s.src = './ui-shell-v1750.js?v=1750d';
  s.defer = true;
  document.head.appendChild(s);
}

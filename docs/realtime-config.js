// v1.7.4 navigation + dated data status + simplified top hierarchy; keeps radar scoring isolated.
window.DOGSON_REALTIME_API = window.DOGSON_REALTIME_API || "";
window.DOGSON_UI_ASSET_VERSION = '1730';

// Keep optional modules separate from the core page so a data-source/UI issue
// cannot break the existing intraday / close radar rendering.
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

if (!document.getElementById('dogson-nav-v1740')) {
  const s = document.createElement('script');
  s.id = 'dogson-nav-v1740';
  s.src = './ui-nav-v1740.js?v=1742';
  s.defer = true;
  document.head.appendChild(s);
}

if (!document.getElementById('dogson-clean-v1743')) {
  const s = document.createElement('script');
  s.id = 'dogson-clean-v1743';
  s.src = './ui-clean-v1743.js?v=1743';
  s.defer = true;
  document.head.appendChild(s);
}

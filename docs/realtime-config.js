// v1.5.32 near-real-time quote backend + decision filter + light dashboard modules.
window.DOGSON_REALTIME_API = window.DOGSON_REALTIME_API || "";

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
  s.src = './ui-filters.js?v=1532';
  s.async = true;
  document.head.appendChild(s);
}

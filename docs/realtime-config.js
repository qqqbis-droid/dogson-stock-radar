// v1.4 near-real-time quote backend + 60K close module loader.
// After the free Vercel API is connected, set this to e.g.
// https://dogson-stock-radar.vercel.app
window.DOGSON_REALTIME_API = window.DOGSON_REALTIME_API || "";

// Keep the 60K module separate from the core page so a data-source issue cannot
// break the existing intraday / close radar rendering.
if (!document.getElementById('dogson-hourly-module')) {
  const s = document.createElement('script');
  s.id = 'dogson-hourly-module';
  s.src = './hourly.js?v=140';
  s.async = true;
  document.head.appendChild(s);
}

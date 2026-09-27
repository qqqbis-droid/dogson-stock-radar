// v1.7.5 stable bootstrap: one UI loader, one shell owner, no duplicate hourly/data fetchers.
window.DOGSON_REALTIME_API = window.DOGSON_REALTIME_API || "";
window.DOGSON_UI_ASSET_VERSION = '1730';

// If a new service worker takes control, reload exactly once so the current
// session moves onto the stabilized cache/data policy without another launch.
if ('serviceWorker' in navigator && !window.__DOGSON_SW_BOOT_RELOAD_1751__) {
  window.__DOGSON_SW_BOOT_RELOAD_1751__ = true;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    const key = 'dogson-sw-boot-reload-1751stable1';
    if (sessionStorage.getItem(key) === '1') return;
    sessionStorage.setItem(key, '1');
    location.reload();
  });
}

// Hide legacy markup immediately on first-run pages that are not yet controlled by the SW.
document.documentElement.classList.add('dogson-booting');
if (!document.getElementById('dogson-boot-v1688')) {
  const st = document.createElement('style');
  st.id = 'dogson-boot-v1688';
  st.textContent = `
    html.dogson-booting body{background:#f5f6f3!important;overflow:hidden!important}
    html.dogson-booting .wrap,html.dogson-booting .footer{opacity:0!important;pointer-events:none!important}
    html.dogson-booting body::before{content:'🐶 犬子老師・飆股雷達';position:fixed;z-index:99998;left:0;right:0;top:42%;transform:translateY(-50%);text-align:center;color:#234d40;font:900 20px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif}
    html.dogson-booting body::after{content:'正在載入穩定版介面…';position:fixed;z-index:99999;left:0;right:0;top:calc(42% + 42px);text-align:center;color:#718078;font:700 13px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif}
  `;
  document.head.appendChild(st);
}

// hourly.js is already loaded by index.html. Do not load a second copy here.
// ui-filters owns the deterministic UI chain, data recovery, and the single shell.
if (!document.getElementById('dogson-decision-filters') && !window.__DOGSON_UI_LOADER_V1730__) {
  const s = document.createElement('script');
  s.id = 'dogson-decision-filters';
  s.src = './ui-filters.js?v=1751stable1';
  s.async = false;
  document.head.appendChild(s);
}

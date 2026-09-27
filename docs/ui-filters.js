(()=>{
  if(window.__DOGSON_UI_LOADER_V1730__) return;
  window.__DOGSON_UI_LOADER_V1730__ = true;
  const src=document.currentScript?.src||location.href;
  const base=new URL('.',src);
  const version='1730';
  let revealed=false;

  function ensureBoot(){
    document.documentElement.classList.add('dogson-booting');
    if(document.getElementById('dogson-boot-v1688'))return;
    const s=document.createElement('style');s.id='dogson-boot-v1688';s.textContent=`
      html.dogson-booting body{background:#f5f6f3!important;overflow:hidden!important}
      html.dogson-booting .wrap,html.dogson-booting .footer{opacity:0!important;pointer-events:none!important}
      html.dogson-booting body::before{content:'🐶 犬子老師・飆股雷達';position:fixed;z-index:99998;left:0;right:0;top:42%;transform:translateY(-50%);text-align:center;color:#234d40;font:900 20px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif;letter-spacing:.02em}
      html.dogson-booting body::after{content:'正在載入穩定版介面…';position:fixed;z-index:99999;left:0;right:0;top:calc(42% + 42px);text-align:center;color:#718078;font:700 13px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif}
    `;document.head.appendChild(s);
  }
  ensureBoot();

  function reveal(){
    if(revealed) return;
    revealed=true;
    document.documentElement.classList.remove('dogson-booting');
    document.documentElement.dataset.dogsonUiReady=version;
    try{window.dispatchEvent(new CustomEvent('dogson:ui-ready',{detail:{version}}))}catch{}
  }

  const safetyTimer=setTimeout(reveal,8000);
  function loadCss(name,id){if(document.getElementById(id))return;const link=document.createElement('link');link.id=id;link.rel='stylesheet';link.href=new URL(name,base).href+'?v='+version;document.head.appendChild(link)}
  function preloadScript(name,assetVersion=version){const href=new URL(name,base).href+'?v='+assetVersion;if(document.querySelector(`link[data-dogson-preload="${href}"]`))return;const l=document.createElement('link');l.rel='preload';l.as='script';l.href=href;l.dataset.dogsonPreload=href;document.head.appendChild(l)}
  function loadScript(name,id,assetVersion=version){return new Promise((resolve,reject)=>{if(document.getElementById(id))return resolve();const s=document.createElement('script');s.id=id;s.src=new URL(name,base).href+'?v='+assetVersion;s.async=false;s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}

  loadCss('redesign-v160.css','dogson-dashboard-css');
  loadCss('redesign-v160-dark.css','dogson-dashboard-dark-css');
  loadCss('contrast-v160.css','dogson-dashboard-contrast-css');
  loadCss('redesign-v162.css','dogson-dashboard-v162-css');
  loadCss('redesign-v162-fix.css','dogson-dashboard-v162-fix-css');
  loadCss('redesign-v163.css','dogson-dashboard-v163-css');
  loadCss('redesign-v164.css','dogson-dashboard-v164-css');
  loadCss('redesign-v165.css','dogson-dashboard-v165-css');
  loadCss('redesign-v166.css','dogson-dashboard-v166-css');
  loadCss('redesign-v1679.css','dogson-dashboard-v1679-css');
  loadCss('redesign-v1685.css','dogson-dashboard-v1685-css');
  loadCss('redesign-v1686.css','dogson-dashboard-v1686-css');
  loadCss('redesign-v1690.css','dogson-dashboard-v1690-css');

  const plan=[
    ['ui-data-bootstrap-v1751.js','dogson-data-bootstrap-v1751','1751data1'],
    ['redesign-v160.js','dogson-redesign-v160',version],
    ['ui-polish-v160.js','dogson-ui-polish-v160',version],
    ['ui-layout-v162.js','dogson-ui-layout-v162',version],
    ['ui-card-v164.js','dogson-ui-card-v164',version],
    ['ui-card-v166.js','dogson-ui-card-v166',version],
    ['ui-fold-v167.js','dogson-ui-fold-v167',version],
    ['ui-entry-v1679.js','dogson-ui-entry-v1679',version],
    ['ui-freshness-v1688.js','dogson-ui-freshness-v1688',version],
    ['ui-system-status-v1700.js','dogson-ui-system-status-v1700','1751light1'],
    ['ui-dual-decision-v1690.js','dogson-ui-dual-decision-v1690',version],
    ['ui-load-more-v1681.js','dogson-ui-load-more-v1681',version],
    ['ui-market-v1685.js','dogson-ui-market-v1685','1750peer1'],
    ['ui-market-ticker-v1686.js','dogson-ui-market-ticker-v1688',version],
    ['ui-page-architecture-v1701.js','dogson-ui-page-architecture-v1701','1750'],
    ['ui-accuracy-guard-v1702.js','dogson-ui-accuracy-guard-v1702','1750peer2'],
    ['ui-runtime-safety-v1720.js','dogson-ui-runtime-safety-v1720',version],
    ['ui-filter-v1730.js','dogson-ui-filter-v1730',version],
    ['ui-shell-v1751.js','dogson-shell-v1751','1751shell1']
  ];

  plan.forEach(([name,,assetVersion])=>preloadScript(name,assetVersion));
  plan.reduce((p,[name,id,assetVersion])=>p.then(()=>loadScript(name,id,assetVersion)),Promise.resolve())
    .then(()=>{clearTimeout(safetyTimer);requestAnimationFrame(()=>requestAnimationFrame(reveal))})
    .catch(err=>{clearTimeout(safetyTimer);reveal();console.warn('Dogson UI module load failed',err)});
})();
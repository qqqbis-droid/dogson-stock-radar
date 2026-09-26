(()=>{
  if(window.__DOGSON_UI_LOADER_V1720__) return;
  window.__DOGSON_UI_LOADER_V1720__ = true;
  const src=document.currentScript?.src||location.href;
  const base=new URL('.',src);
  const version='1720';
  let revealed=false;

  function reveal(){
    if(revealed) return;
    revealed=true;
    document.documentElement.classList.remove('dogson-booting');
    document.documentElement.dataset.dogsonUiReady=version;
  }

  const safetyTimer=setTimeout(reveal,4500);
  function loadCss(name,id){if(document.getElementById(id))return;const link=document.createElement('link');link.id=id;link.rel='stylesheet';link.href=new URL(name,base).href+'?v='+version;document.head.appendChild(link)}
  function loadScript(name,id){return new Promise((resolve,reject)=>{if(document.getElementById(id))return resolve();const s=document.createElement('script');s.id=id;s.src=new URL(name,base).href+'?v='+version;s.defer=true;s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}

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
  loadScript('ui-filters-core-v1531.js','dogson-filter-core-v1531')
    .then(()=>loadScript('redesign-v160.js','dogson-redesign-v160'))
    .then(()=>loadScript('ui-polish-v160.js','dogson-ui-polish-v160'))
    .then(()=>loadScript('ui-layout-v162.js','dogson-ui-layout-v162'))
    .then(()=>loadScript('ui-card-v164.js','dogson-ui-card-v164'))
    .then(()=>loadScript('ui-card-v166.js','dogson-ui-card-v166'))
    .then(()=>loadScript('ui-fold-v167.js','dogson-ui-fold-v167'))
    .then(()=>loadScript('ui-entry-v1679.js','dogson-ui-entry-v1679'))
    .then(()=>loadScript('ui-freshness-v1688.js','dogson-ui-freshness-v1688'))
    .then(()=>loadScript('ui-system-status-v1700.js','dogson-ui-system-status-v1700'))
    .then(()=>loadScript('ui-dual-decision-v1690.js','dogson-ui-dual-decision-v1690'))
    .then(()=>loadScript('ui-load-more-v1681.js','dogson-ui-load-more-v1681'))
    .then(()=>loadScript('ui-market-v1685.js','dogson-ui-market-v1685'))
    .then(()=>loadScript('ui-market-ticker-v1686.js','dogson-ui-market-ticker-v1688'))
    .then(()=>loadScript('ui-page-architecture-v1701.js','dogson-ui-page-architecture-v1701'))
    .then(()=>loadScript('ui-accuracy-guard-v1702.js','dogson-ui-accuracy-guard-v1702'))
    .then(()=>loadScript('ui-runtime-safety-v1720.js','dogson-ui-runtime-safety-v1720'))
    .then(()=>{clearTimeout(safetyTimer);requestAnimationFrame(()=>requestAnimationFrame(reveal))})
    .catch(err=>{clearTimeout(safetyTimer);reveal();console.warn('Dogson UI module load failed',err)});
})();

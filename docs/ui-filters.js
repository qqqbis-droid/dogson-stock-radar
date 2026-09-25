(()=>{
  if(window.__DOGSON_UI_LOADER_V1676__) return;
  window.__DOGSON_UI_LOADER_V1676__ = true;
  const src=document.currentScript?.src||location.href;
  const base=new URL('.',src);
  const version='1676';

  function loadCss(name,id){
    if(document.getElementById(id)) return;
    const link=document.createElement('link');
    link.id=id;link.rel='stylesheet';link.href=new URL(name,base).href+'?v='+version;
    document.head.appendChild(link);
  }
  function loadScript(name,id){
    return new Promise((resolve,reject)=>{
      if(document.getElementById(id)) return resolve();
      const s=document.createElement('script');s.id=id;s.src=new URL(name,base).href+'?v='+version;s.defer=true;
      s.onload=resolve;s.onerror=reject;document.head.appendChild(s);
    });
  }

  loadCss('redesign-v160.css','dogson-dashboard-css');
  loadCss('redesign-v160-dark.css','dogson-dashboard-dark-css');
  loadCss('contrast-v160.css','dogson-dashboard-contrast-css');
  loadCss('redesign-v162.css','dogson-dashboard-v162-css');
  loadCss('redesign-v162-fix.css','dogson-dashboard-v162-fix-css');
  loadCss('redesign-v163.css','dogson-dashboard-v163-css');
  loadCss('redesign-v164.css','dogson-dashboard-v164-css');
  loadCss('redesign-v165.css','dogson-dashboard-v165-css');
  loadCss('redesign-v166.css','dogson-dashboard-v166-css');
  loadScript('ui-filters-core-v1531.js','dogson-filter-core-v1531')
    .then(()=>loadScript('redesign-v160.js','dogson-redesign-v160'))
    .then(()=>loadScript('ui-polish-v160.js','dogson-ui-polish-v160'))
    .then(()=>loadScript('ui-layout-v162.js','dogson-ui-layout-v162'))
    .then(()=>loadScript('ui-card-v164.js','dogson-ui-card-v164'))
    .then(()=>loadScript('ui-card-v166.js','dogson-ui-card-v166'))
    .then(()=>loadScript('ui-fold-v167.js','dogson-ui-fold-v167'))
    .catch(err=>console.warn('Dogson UI module load failed',err));
})();

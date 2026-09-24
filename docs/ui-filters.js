(()=>{
  if(window.__DOGSON_UI_LOADER_V1532__) return;
  window.__DOGSON_UI_LOADER_V1532__ = true;
  const src=document.currentScript?.src||location.href;
  const base=new URL('.',src);
  const version='1532-1';

  function loadCss(name){
    const id='dogson-light-redesign-css';
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

  loadCss('redesign-v1532.css');
  loadScript('ui-filters-core-v1531.js','dogson-filter-core-v1531')
    .then(()=>loadScript('redesign-v1532.js','dogson-redesign-v1532'))
    .catch(err=>console.warn('Dogson UI module load failed',err));
})();

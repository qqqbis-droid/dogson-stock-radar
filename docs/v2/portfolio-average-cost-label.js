(()=>{
'use strict';
function patch(){
  document.querySelectorAll('#portfolioDetailBody .portfolio-detail-grid span').forEach(el=>{
    if(el.textContent.trim()==='成本') el.textContent='平均成本';
  });
  document.querySelectorAll('#portfolioCards .portfolio-card .muted').forEach(el=>{
    const t=el.textContent||'';
    if(/^成本\s/.test(t.trim())) el.textContent=t.replace(/^\s*成本\s+/,'平均成本 ');
  });
}
function loadBrand(){
  if(document.querySelector('script[src*="brand-inuko-lab.js"]'))return;
  if(document.querySelector('script[data-inuko-brand-loader]'))return;
  const s=document.createElement('script');
  s.src='./brand-inuko-lab.js?v=20261001b';
  s.dataset.inukoBrandLoader='1';
  s.defer=true;
  document.head.appendChild(s);
}
function boot(){
  loadBrand();
  patch();
  const detail=document.getElementById('portfolioDetailBody');
  const cards=document.getElementById('portfolioCards');
  const obs=new MutationObserver(patch);
  if(detail) obs.observe(detail,{childList:true,subtree:true});
  if(cards) obs.observe(cards,{childList:true,subtree:true});
  document.addEventListener('radar:portfolio-changed',()=>setTimeout(patch,0));
  document.addEventListener('radar:view-rendered',()=>setTimeout(patch,0));
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();

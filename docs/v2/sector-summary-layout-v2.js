(()=>{
'use strict';
const STYLE_ID='sectorSummaryLayoutV2Style';
let raf=0;
function ensureStyle(){
  if(document.getElementById(STYLE_ID))return;
  const s=document.createElement('style');
  s.id=STYLE_ID;
  s.textContent=`
#sectorList.chips{gap:12px;align-items:stretch}
#sectorList .sector-summary-card-v2{min-width:252px;max-width:286px;padding:14px 14px 12px;border-radius:18px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;align-content:start;box-sizing:border-box}
#sectorList .sector-summary-card-v2> b{grid-column:1;align-self:center;font-size:.98rem;line-height:1.25;margin:0}
#sectorList .sector-summary-card-v2> strong{grid-column:2;align-self:center;text-align:right;font-size:1.12rem;line-height:1.2;white-space:nowrap}
#sectorList .sector-summary-card-v2>div:not(.capital-more):not(.capital-hint):not(.live-sector-preview){grid-column:1/-1;color:var(--muted);font-size:.77rem;line-height:1.42}
#sectorList .sector-summary-card-v2>.capital-hint.sector-summary-actions{grid-column:1/-1;margin-top:5px;padding-top:9px;border-top:1px dashed var(--line);display:flex;justify-content:space-between;align-items:center;gap:10px;color:var(--green);font-weight:850;font-size:.72rem;line-height:1.2}
#sectorList .sector-summary-card-v2>.capital-hint.sector-summary-actions span:last-child{color:var(--muted);font-weight:700}
#sectorList .sector-summary-card-v2>.capital-more{grid-column:1/-1;margin-top:2px;padding-top:10px;border-top:1px solid var(--line);grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
#sectorList .sector-summary-card-v2>.capital-more:not([hidden]){display:grid}
#sectorList .sector-summary-card-v2>.capital-more .mc-row{display:flex;flex-direction:column;justify-content:flex-start;gap:2px;padding:8px 9px;border-radius:10px;background:color-mix(in srgb,var(--soft) 76%,transparent);min-width:0}
#sectorList .sector-summary-card-v2>.capital-more .mc-row span{font-size:.66rem;color:var(--muted)}
#sectorList .sector-summary-card-v2>.capital-more .mc-row b{font-size:.8rem;line-height:1.25;overflow-wrap:anywhere}
#sectorList .sector-summary-card-v2>.capital-more>.capital-hint{grid-column:1/-1;margin-top:2px;font-size:.67rem;line-height:1.4}
#sectorList .sector-summary-card-v2 .member-list,
#sectorList .sector-summary-card-v2 .capital-section-label,
#sectorList .sector-summary-card-v2 .live-sector-preview,
#sectorList .sector-summary-card-v2 .live-sector-members{display:none!important}
#sectorRankExplain{margin-top:12px}
#sectorRankExplain .sector-rank-panel,
#sectorRankExplain .live-sector-rank{padding:13px;border-radius:16px;background:var(--soft);border:1px solid var(--line)}
#sectorRankExplain .sector-rank-head,
#sectorRankExplain .live-sector-rank-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:8px}
#sectorRankExplain .sector-rank-head b,
#sectorRankExplain .live-sector-rank-head b{font-size:.9rem}
#sectorRankExplain .sector-rank-head span,
#sectorRankExplain .live-sector-rank-head span{font-size:.68rem;color:var(--muted);white-space:nowrap}
#sectorRankExplain .sector-rank-note{margin:0 0 8px;font-size:.68rem;line-height:1.4;color:var(--muted)}
#sectorRankExplain .sector-rank-list,
#sectorRankExplain .live-sector-rank-list{display:grid;gap:7px}
#sectorRankExplain .sector-rank-row,
#sectorRankExplain .live-sector-rank-row{width:100%;display:grid;grid-template-columns:30px minmax(0,1fr) 98px;gap:8px;align-items:center;padding:9px 10px;border-radius:12px;background:var(--card);border:1px solid var(--line);text-align:left;color:var(--ink);box-sizing:border-box}
#sectorRankExplain .sector-rank-no,
#sectorRankExplain .live-sector-rank-row> b:first-child{font-size:.8rem;font-weight:900;color:var(--green);text-align:center}
#sectorRankExplain .sector-rank-id b,
#sectorRankExplain .live-sector-rank-row strong{font-size:.8rem;line-height:1.25}
#sectorRankExplain .sector-rank-id small,
#sectorRankExplain .live-sector-rank-row small{display:block;margin-top:3px;color:var(--muted);font-size:.66rem;line-height:1.3}
#sectorRankExplain .sector-rank-score,
#sectorRankExplain .live-sector-rank-score{text-align:right;font-size:.65rem;color:var(--muted)}
#sectorRankExplain .sector-rank-score b,
#sectorRankExplain .live-sector-rank-score b{font-size:.84rem;color:var(--ink)}
@media(max-width:560px){
  #sectorList .sector-summary-card-v2{min-width:248px;max-width:268px;padding:13px}
  #sectorList .sector-summary-card-v2>.capital-more{grid-template-columns:repeat(2,minmax(0,1fr))}
  #sectorRankExplain .sector-rank-row,#sectorRankExplain .live-sector-rank-row{grid-template-columns:28px minmax(0,1fr) 84px;padding:9px 8px}
}
`;
  document.head.appendChild(s);
}
function actionText(chip){
  const open=chip.getAttribute('aria-expanded')==='true';
  return `<span>${open?'收合族群明細 ↑':'查看族群明細'}</span><span>同族群股票 ↓</span>`;
}
function patchTop(){
  document.querySelectorAll('#sectorList .capital-chip').forEach(chip=>{
    chip.classList.add('sector-summary-card-v2');
    chip.querySelectorAll(':scope > .live-sector-preview, :scope > .capital-more .member-list, :scope > .capital-more .capital-section-label, :scope > .capital-more .live-sector-members').forEach(el=>{el.style.display='none'});
    const hint=chip.querySelector(':scope > .capital-hint');
    if(hint){
      hint.classList.add('sector-summary-actions');
      const html=actionText(chip);
      if(hint.innerHTML!==html)hint.innerHTML=html;
    }
  });
}
function patchLower(){
  const box=document.getElementById('sectorRankExplain');
  if(!box)return;
  box.querySelectorAll('.sector-rank-head b').forEach(el=>{
    const next=(el.textContent||'').replace('｜族群內先看','｜同族群股票');
    if(el.textContent!==next)el.textContent=next;
  });
  box.querySelectorAll('.sector-rank-note').forEach(el=>{
    const next='依目前頁面正式排序顯示；點股票可直接查看完整個股。';
    if(el.textContent!==next)el.textContent=next;
  });
}
function patch(){raf=0;ensureStyle();patchTop();patchLower()}
function schedule(){if(raf)return;raf=requestAnimationFrame(patch)}
function boot(){
  patch();
  const sector=document.getElementById('sectorList');
  const rank=document.getElementById('sectorRankExplain');
  if(sector)new MutationObserver(schedule).observe(sector,{childList:true,subtree:true});
  if(rank)new MutationObserver(schedule).observe(rank,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target.closest?.('#sectorList [data-capital-expand]'))setTimeout(schedule,0)});
  document.addEventListener('radar:view-rendered',()=>setTimeout(schedule,0));
  document.addEventListener('radar:data-reloaded',()=>setTimeout(schedule,0));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

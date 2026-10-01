(()=>{
'use strict';
const num=v=>{const n=Number(String(v??'').replace(/,/g,''));return Number.isFinite(n)?n:null};
const signed=(v,d=2)=>v==null?'—':`${v>0?'+':''}${Number(v).toLocaleString('zh-TW',{minimumFractionDigits:d,maximumFractionDigits:d})}`;
let timer=null;
function pointMove(close,pct){if(close==null||pct==null||pct<=-100)return null;const prev=close/(1+pct/100);return close-prev}
function patch(){
 const cells=document.querySelectorAll('#livePinnedBar .live-pulse-item');
 [0,1].forEach(i=>{
  const cell=cells[i],priceEl=cell?.querySelector('b'),small=cell?.querySelector('small');
  if(!priceEl||!small)return;
  const close=num(priceEl.textContent),m=String(small.textContent||'').match(/([+-]?\d+(?:\.\d+)?)%/),pct=m?num(m[1]):null;
  if(close==null||pct==null)return;
  const move=pointMove(close,pct),next=`${signed(move)} · ${signed(pct)}%`;
  if(small.textContent!==next)small.textContent=next;
  small.classList.add('live-pulse-delta');
 });
}
function schedule(){clearTimeout(timer);timer=setTimeout(patch,25)}
function boot(){
 if(!document.getElementById('livePulsePointsStyle')){const s=document.createElement('style');s.id='livePulsePointsStyle';s.textContent='.live-pulse-delta{font-variant-numeric:tabular-nums;letter-spacing:-.01em}@media(max-width:560px){.live-pulse-delta{font-size:.57rem!important}}';document.head.appendChild(s)}
 schedule();
 const bar=document.getElementById('livePinnedBar');
 if(bar)new MutationObserver(schedule).observe(bar,{childList:true,subtree:true,characterData:true});
 document.addEventListener('radar:data-reloaded',schedule);
 document.addEventListener('radar:view-rendered',schedule);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

(()=>{
  'use strict';

  let token=0;
  let current={code:'',view:''};
  const timers=new Set();
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

  function clearTimers(){
    for(const id of timers)clearTimeout(id);
    timers.clear();
  }
  function later(fn,ms){
    const id=setTimeout(()=>{timers.delete(id);fn()},ms);
    timers.add(id);
    return id;
  }
  function body(){return document.getElementById('detailBody')}
  function dialog(){return document.getElementById('detailDialog')}
  function cardFor(code){
    const cards=[...document.querySelectorAll('#cards .card[data-code]')];
    return cards.find(x=>String(x.dataset.code||'').trim()===String(code||'').trim())||null;
  }
  function fallbackHtml(code,view,late=false){
    const label=view==='close'?'盤後':view==='daytrade'?'當沖':'盤中';
    return `<div class="dlg-fast-fallback" data-detail-fast-fallback="1">
      <div class="dlg-fast-note ${late?'late':''}">
        <b>${late?'完整詳情載入逾時':'完整詳情仍在載入'}</b>
        <span>${late?'先保留你點選當下的列表快照；可重試完整詳情。':'先顯示你剛剛看到的列表快照，正式詳情完成後會自動替換。'}</span>
        <small>${esc(label)}資料不跨日補猜；這裡只是目前列表快照，不冒充完整詳情。</small>
      </div>
      <div class="dlg-fast-card-host"></div>
      <button type="button" class="dlg-fast-retry" data-detail-retry="1">重新載入完整詳情</button>
    </div>`;
  }
  function showFallback(code,view,late=false){
    const b=body(),d=dialog();
    if(!b||!d?.open)return;
    const stillInitial=!!b.querySelector('.detail-loading');
    const existing=b.querySelector('[data-detail-fast-fallback]');
    if(!stillInitial&&!existing)return;
    if(!existing)b.innerHTML=fallbackHtml(code,view,late);
    const wrap=b.querySelector('[data-detail-fast-fallback]');
    if(!wrap)return;
    if(late){
      const note=wrap.querySelector('.dlg-fast-note');
      if(note){
        note.classList.add('late');
        const bold=note.querySelector('b');if(bold)bold.textContent='完整詳情載入逾時';
        const span=note.querySelector('span');if(span)span.textContent='先保留你點選當下的列表快照；可重試完整詳情。';
      }
    }
    const host=wrap.querySelector('.dlg-fast-card-host');
    if(host&&!host.firstElementChild){
      const src=cardFor(code);
      if(src){
        const clone=src.cloneNode(true);
        clone.removeAttribute('role');clone.removeAttribute('tabindex');clone.removeAttribute('aria-label');
        clone.removeAttribute('data-code');
        clone.classList.add('dlg-fast-card');
        clone.style.pointerEvents='none';
        host.appendChild(clone);
      }else{
        host.innerHTML=`<div class="detail-note warn">${esc(code)} 的列表快照目前不在畫面中，但完整詳情仍可重試。</div>`;
      }
    }
  }
  function start(e){
    const code=String(e.detail?.code||'').trim();
    const view=String(e.detail?.view||document.querySelector('.tab.active')?.dataset.view||'intraday');
    if(!code)return;
    token+=1;const mine=token;current={code,view};clearTimers();
    later(()=>{if(mine===token)showFallback(code,view,false)},1200);
    later(()=>{if(mine===token)showFallback(code,view,true)},8000);
  }
  function resolved(){
    const b=body();
    if(!b)return;
    if(!b.querySelector('.detail-loading')&&!b.querySelector('[data-detail-fast-fallback]'))clearTimers();
  }
  function retry(){
    if(!current.code)return;
    const b=body();if(b)b.innerHTML='<div class="detail-loading"><b>重新讀取個股詳情…</b><p class="muted">先載入核心決策，再補支撐壓力與技術／籌碼證據。</p></div>';
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:current.code,view:current.view}}));
  }
  function style(){
    if(document.getElementById('detailLoadingGuardStyle'))return;
    const s=document.createElement('style');s.id='detailLoadingGuardStyle';s.textContent=`
      .dlg-fast-fallback{padding:2px 0 12px}.dlg-fast-note{padding:10px 11px;border-radius:11px;background:var(--soft);border:1px solid var(--line);margin-bottom:10px}.dlg-fast-note.late{border-color:color-mix(in srgb,var(--red) 35%,var(--line));background:color-mix(in srgb,var(--red) 6%,var(--soft))}.dlg-fast-note b,.dlg-fast-note span,.dlg-fast-note small{display:block}.dlg-fast-note b{font-size:.86rem}.dlg-fast-note span{margin-top:4px;font-size:.75rem;line-height:1.45}.dlg-fast-note small{margin-top:5px;color:var(--muted);font-size:.67rem;line-height:1.4}.dlg-fast-card-host>.card{margin:0;box-shadow:none}.dlg-fast-retry{display:block;width:100%;margin-top:10px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:inherit;font-weight:750}
    `;document.head.appendChild(s);
  }
  function boot(){
    style();
    document.addEventListener('radar:open-stock',start);
    document.addEventListener('radar:detail-core-rendered',resolved);
    document.addEventListener('radar:detail-rendered',resolved);
    document.addEventListener('click',e=>{if(e.target.closest?.('[data-detail-retry]'))retry()});
    document.addEventListener('close',e=>{if(e.target?.id==='detailDialog'){token+=1;clearTimers()}},true);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

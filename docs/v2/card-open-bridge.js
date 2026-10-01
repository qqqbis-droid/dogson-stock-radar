(function(){
  'use strict';
  const CARD_SELECTOR='#cards .card[data-code]';
  const CONTROL_SELECTOR='button,a,input,select,textarea,summary,label,[data-portfolio-edit],[data-portfolio-action]';
  const ELITE_LIMIT=8,QUALITY_MIN=75,POSITION_MIN=65,CONFIDENCE_MIN=80;
  let lastOpen={code:'',at:0};
  let policyTimer=null;

  function cardFromTarget(target){return target?.closest?.(CARD_SELECTOR)||null}
  function isControl(target,card){const c=target?.closest?.(CONTROL_SELECTOR);return Boolean(c&&card?.contains(c))}
  function n(text){const m=String(text||'').replace(/,/g,'').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null}
  function activeView(){return document.querySelector('.tab.active')?.dataset?.view||'intraday'}

  function primeDialog(code){
    if(activeView()==='portfolio')return;
    const dialog=document.getElementById('detailDialog');
    const title=document.getElementById('detailTitle');
    const body=document.getElementById('detailBody');
    if(!dialog||!title||!body)return;
    title.textContent=`${String(code||'').trim()} 個股詳情`;
    body.innerHTML='<div class="muted">讀取個股詳情…</div>';
    if(dialog.open)return;
    try{dialog.showModal()}
    catch(err){dialog.setAttribute('open','');dialog.classList.add('detail-dialog-fallback');console.warn('detail dialog fallback',err)}
  }

  function openCode(code){
    code=String(code||'').trim();
    if(!code)return;
    const now=Date.now();
    if(lastOpen.code===code&&now-lastOpen.at<350)return;
    lastOpen={code,at:now};
    primeDialog(code);
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code,source:'card'}}));
  }

  function isClose(){return activeView()==='close'}
  function nextDayActive(){return document.querySelector('[data-quick-filter="NEXT_DAY_READY"]')?.classList.contains('active')===true}
  function scoreValues(card){
    const cells=[...card.querySelectorAll('.score-row .score')];
    return {quality:n(cells[0]?.querySelector('b')?.textContent),position:n(cells[1]?.querySelector('b')?.textContent),confidence:n(cells[2]?.querySelector('b')?.textContent)};
  }
  function elite(card){
    const v=scoreValues(card),rank=String(card.querySelector('.rank')?.textContent||'');
    return /明日候選/.test(rank)&&v.quality!=null&&v.quality>=QUALITY_MIN&&v.position!=null&&v.position>=POSITION_MIN&&v.confidence!=null&&v.confidence>=CONFIDENCE_MIN;
  }
  function setText(el,value){if(el&&el.textContent!==value)el.textContent=value}
  function applyNextDayPolicy(){
    if(!isClose())return;
    const tile=document.querySelector('[data-quick-filter="NEXT_DAY_READY"]');
    const cards=[...document.querySelectorAll(CARD_SELECTOR)];
    cards.forEach(c=>{if(c.dataset.eliteHidden==='1'){c.style.display='';delete c.dataset.eliteHidden}});
    const eligible=cards.filter(elite).slice(0,ELITE_LIMIT),count=eligible.length;
    setText(tile?.querySelector('strong'),String(count));
    setText(tile?.querySelector('small'),`品質≥${QUALITY_MIN}・位置≥${POSITION_MIN}・信心≥${CONFIDENCE_MIN}・最多${ELITE_LIMIT}檔`);
    if(nextDayActive()){
      const keep=new Set(eligible);
      cards.forEach(card=>{if(!keep.has(card)){card.style.display='none';card.dataset.eliteHidden='1'}});
      setText(document.getElementById('countText'),`明日候選 · ${count} 檔`);
      document.getElementById('loadMore')?.classList.add('hidden');
    }
  }
  function schedulePolicy(delay=160){clearTimeout(policyTimer);policyTimer=setTimeout(applyNextDayPolicy,delay)}

  document.addEventListener('radar:open-stock',event=>{
    const code=String(event.detail?.code||'').trim();
    if(code)primeDialog(code);
  });

  document.addEventListener('click',event=>{
    const card=cardFromTarget(event.target);
    if(card&&!isControl(event.target,card)){
      event.preventDefault();
      openCode(card.dataset.code);
      return;
    }
    if(event.target?.closest?.('[data-quick-filter], [data-quick-filter-clear], .tab, #loadMore')){
      schedulePolicy(180);
      if(event.target.closest?.('[data-quick-filter="NEXT_DAY_READY"], [data-quick-filter-clear]'))setTimeout(applyNextDayPolicy,750);
    }
  });

  document.addEventListener('change',event=>{
    if(event.target?.matches?.('#stageFilter,#actionFilter,#positionFilter,#sectorFilter'))schedulePolicy(220);
  });

  document.addEventListener('keydown',event=>{
    if(event.key!=='Enter'&&event.key!==' ')return;
    const card=cardFromTarget(event.target);
    if(!card||event.target!==card)return;
    event.preventDefault();
    openCode(card.dataset.code);
  });

  document.addEventListener('radar:view-rendered',()=>schedulePolicy(120));
  document.addEventListener('radar:data-reloaded',()=>schedulePolicy(180));
  setTimeout(applyNextDayPolicy,260);
})();

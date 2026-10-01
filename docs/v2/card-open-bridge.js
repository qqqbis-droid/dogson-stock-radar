(function(){
  const CARD_SELECTOR='#cards .card[data-code]';
  const CONTROL_SELECTOR='button,a,input,select,textarea,summary,label,[data-portfolio-edit],[data-portfolio-action]';
  const ELITE_LIMIT=8,QUALITY_MIN=75,POSITION_MIN=65,CONFIDENCE_MIN=80;
  let lastOpen={code:'',at:0};

  function openCode(code){
    code=String(code||'').trim();
    if(!code)return;
    const now=Date.now();
    if(lastOpen.code===code&&now-lastOpen.at<500)return;
    lastOpen={code,at:now};
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code}}));
  }

  function cardFromTarget(target){return target?.closest?.(CARD_SELECTOR)||null}
  function isControl(target,card){
    const c=target?.closest?.(CONTROL_SELECTOR);
    return Boolean(c&&c!==card&&card?.contains(c));
  }
  function n(text){const m=String(text||'').replace(/,/g,'').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null}
  function isClose(){return document.querySelector('.tab.active')?.dataset?.view==='close'}
  function nextDayActive(){return document.querySelector('[data-quick-filter="NEXT_DAY_READY"]')?.classList.contains('active')===true}
  function scoreValues(card){
    const cells=[...card.querySelectorAll('.score-row .score')];
    return {
      quality:n(cells[0]?.querySelector('b')?.textContent),
      position:n(cells[1]?.querySelector('b')?.textContent),
      confidence:n(cells[2]?.querySelector('b')?.textContent)
    };
  }
  function elite(card){
    const v=scoreValues(card);
    const rank=String(card.querySelector('.rank')?.textContent||'');
    return /明日候選/.test(rank)&&v.quality!=null&&v.quality>=QUALITY_MIN&&v.position!=null&&v.position>=POSITION_MIN&&v.confidence!=null&&v.confidence>=CONFIDENCE_MIN;
  }
  function setText(el,value){if(el&&el.textContent!==value)el.textContent=value}

  function applyNextDayPolicy(){
    if(!isClose())return;
    const tile=document.querySelector('[data-quick-filter="NEXT_DAY_READY"]');
    const cards=[...document.querySelectorAll(CARD_SELECTOR)];
    cards.forEach(c=>{if(c.dataset.eliteHidden==='1'){c.style.display='';delete c.dataset.eliteHidden}});
    const eligible=cards.filter(elite).slice(0,ELITE_LIMIT);
    const count=eligible.length;
    setText(tile?.querySelector('strong'),String(count));
    setText(tile?.querySelector('small'),`品質≥${QUALITY_MIN}・位置≥${POSITION_MIN}・最多${ELITE_LIMIT}檔`);
    if(nextDayActive()){
      const keep=new Set(eligible);
      cards.forEach(card=>{if(!keep.has(card)){card.style.display='none';card.dataset.eliteHidden='1'}});
      setText(document.getElementById('countText'),`明日候選 · ${count} 檔`);
      document.getElementById('loadMore')?.classList.add('hidden');
    }
  }

  function decorate(){
    document.querySelectorAll(CARD_SELECTOR).forEach(card=>{
      card.setAttribute('role','button');
      card.setAttribute('tabindex','0');
      card.setAttribute('aria-label',`查看 ${card.dataset.code||''} 個股詳情`);
    });
  }

  // Important: use real click only. pointerup fires after scroll gestures on iPhone and
  // previously started expensive detail loads while the user was merely scrolling.
  document.addEventListener('click',function(event){
    const card=cardFromTarget(event.target);
    if(card&&!isControl(event.target,card))openCode(card.dataset.code);

    if(event.target?.closest?.('[data-quick-filter], [data-quick-filter-clear], .tab, #loadMore')){
      setTimeout(()=>{decorate();applyNextDayPolicy()},120);
      setTimeout(applyNextDayPolicy,700);
    }
  });

  document.addEventListener('change',function(event){
    if(event.target?.matches?.('#stageFilter,#actionFilter,#positionFilter,#sectorFilter')){
      setTimeout(()=>{decorate();applyNextDayPolicy()},120);
    }
  });

  document.addEventListener('keydown',function(event){
    if(event.key!=='Enter'&&event.key!==' ')return;
    const card=cardFromTarget(event.target);
    if(!card||event.target!==card)return;
    event.preventDefault();
    openCode(card.dataset.code);
  });

  document.addEventListener('radar:view-rendered',()=>setTimeout(()=>{decorate();applyNextDayPolicy()},30));
  document.addEventListener('radar:data-reloaded',()=>setTimeout(()=>{decorate();applyNextDayPolicy()},30));
  setTimeout(()=>{decorate();applyNextDayPolicy()},250);
})();

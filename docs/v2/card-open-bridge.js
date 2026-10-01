(function(){
  const CARD_SELECTOR='#cards .card[data-code]';
  const CONTROL_SELECTOR='button,a,input,select,textarea,summary,label,[data-portfolio-edit],[data-portfolio-action]';
  const ELITE_LIMIT=8,QUALITY_MIN=75,POSITION_MIN=65,CONFIDENCE_MIN=80;
  let lastOpen={code:'',at:0},policyBusy=false;

  function openCode(code){
    code=String(code||'').trim();
    if(!code)return;
    const now=Date.now();
    if(lastOpen.code===code&&now-lastOpen.at<450)return;
    lastOpen={code,at:now};
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code}}));
  }

  function cardFromTarget(target){return target?.closest?.(CARD_SELECTOR)||null}
  function isControl(target,card){const c=target?.closest?.(CONTROL_SELECTOR);return Boolean(c&&card?.contains(c))}
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

  function applyNextDayPolicy(){
    if(policyBusy)return;policyBusy=true;
    try{
      const tile=document.querySelector('[data-quick-filter="NEXT_DAY_READY"]');
      const cards=[...document.querySelectorAll(CARD_SELECTOR)];
      cards.forEach(c=>{if(c.dataset.eliteHidden==='1'){c.style.display='';delete c.dataset.eliteHidden}});
      if(!isClose())return;
      const eligible=cards.filter(elite).slice(0,ELITE_LIMIT);
      const count=eligible.length;
      const strong=tile?.querySelector('strong');if(strong)strong.textContent=String(count);
      const small=tile?.querySelector('small');if(small)small.textContent=`品質≥${QUALITY_MIN}・位置≥${POSITION_MIN}・最多${ELITE_LIMIT}檔`;
      if(nextDayActive()){
        const keep=new Set(eligible);
        cards.forEach(card=>{if(!keep.has(card)){card.style.display='none';card.dataset.eliteHidden='1'}});
        const ct=document.getElementById('countText');if(ct)ct.textContent=`明日候選 · ${count} 檔`;
        const more=document.getElementById('loadMore');if(more)more.classList.add('hidden');
      }
    }finally{policyBusy=false}
  }

  document.addEventListener('pointerup',function(event){
    if(event.pointerType==='mouse')return;
    const card=cardFromTarget(event.target);
    if(!card||isControl(event.target,card))return;
    event.preventDefault();
    openCode(card.dataset.code);
  },true);

  document.addEventListener('click',function(event){
    const card=cardFromTarget(event.target);
    if(card&&!isControl(event.target,card)){
      event.preventDefault();
      openCode(card.dataset.code);
    }
    if(event.target?.closest?.('[data-quick-filter], [data-quick-filter-clear], .tab, #loadMore'))setTimeout(applyNextDayPolicy,40);
  });

  document.addEventListener('keydown',function(event){
    if(event.key!=='Enter'&&event.key!==' ')return;
    const card=cardFromTarget(event.target);
    if(!card||event.target!==card)return;
    event.preventDefault();
    openCode(card.dataset.code);
  });

  function decorate(){
    document.querySelectorAll(CARD_SELECTOR).forEach(card=>{
      card.setAttribute('role','button');
      card.setAttribute('tabindex','0');
      card.setAttribute('aria-label',`查看 ${card.dataset.code||''} 個股詳情`);
      card.style.touchAction='manipulation';
    });
    applyNextDayPolicy();
  }
  decorate();
  const cards=document.getElementById('cards');
  if(cards)new MutationObserver(()=>requestAnimationFrame(decorate)).observe(cards,{childList:true,subtree:true});
  const summary=document.getElementById('radarSummary');
  if(summary)new MutationObserver(()=>requestAnimationFrame(applyNextDayPolicy)).observe(summary,{childList:true,subtree:true});
  document.addEventListener('radar:view-rendered',()=>setTimeout(decorate,20));
  document.addEventListener('radar:data-reloaded',()=>setTimeout(decorate,20));
})();

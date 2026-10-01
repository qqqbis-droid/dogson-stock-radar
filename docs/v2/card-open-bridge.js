(function(){
  const CARD_SELECTOR='#cards .card[data-code]';
  const CONTROL_SELECTOR='button,a,input,select,textarea,summary,label,[data-portfolio-edit],[data-portfolio-action]';
  let lastOpen={code:'',at:0};

  function safeShow(dialog){
    if(!dialog||dialog.open)return;
    try{
      if(typeof dialog.showModal==='function')dialog.showModal();
      else dialog.setAttribute('open','');
    }catch(_){
      dialog.setAttribute('open','');
      dialog.classList.add('dialog-fallback-open');
    }
  }

  function showLoading(code){
    const dialog=document.getElementById('detailDialog');
    const title=document.getElementById('detailTitle');
    const body=document.getElementById('detailBody');
    if(title)title.textContent=code||'個股詳情';
    if(body)body.innerHTML='<div class="muted">讀取個股資訊…</div>';
    safeShow(dialog);
  }

  function openCode(code){
    code=String(code||'').trim();
    if(!code)return;
    const now=Date.now();
    if(lastOpen.code===code&&now-lastOpen.at<450)return;
    lastOpen={code,at:now};
    showLoading(code);
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code}}));
  }

  function cardFromTarget(target){return target?.closest?.(CARD_SELECTOR)||null}
  function isControl(target,card){const c=target?.closest?.(CONTROL_SELECTOR);return Boolean(c&&card?.contains(c))}

  document.addEventListener('radar:open-stock',function(event){
    const code=String(event.detail?.code||'').trim();
    if(code)showLoading(code);
  },true);

  document.addEventListener('pointerup',function(event){
    if(event.pointerType==='mouse')return;
    const card=cardFromTarget(event.target);
    if(!card||isControl(event.target,card))return;
    event.preventDefault();
    openCode(card.dataset.code);
  },true);

  document.addEventListener('click',function(event){
    const card=cardFromTarget(event.target);
    if(!card||isControl(event.target,card))return;
    event.preventDefault();
    openCode(card.dataset.code);
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
  }
  decorate();
  const cards=document.getElementById('cards');
  if(cards)new MutationObserver(decorate).observe(cards,{childList:true,subtree:true});
})();

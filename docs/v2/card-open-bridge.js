(function(){
  'use strict';
  const CARD_SELECTOR='#cards .card[data-code]';
  const CONTROL_SELECTOR='button,a,input,select,textarea,summary,label,[data-portfolio-edit],[data-portfolio-action]';
  let lastOpen={code:'',at:0};

  function cardFromTarget(target){return target?.closest?.(CARD_SELECTOR)||null}
  function isControl(target,card){const c=target?.closest?.(CONTROL_SELECTOR);return Boolean(c&&card?.contains(c))}
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

  document.addEventListener('radar:open-stock',event=>{
    const code=String(event.detail?.code||'').trim();
    if(code)primeDialog(code);
  });

  document.addEventListener('click',event=>{
    const card=cardFromTarget(event.target);
    if(card&&!isControl(event.target,card)){
      event.preventDefault();
      openCode(card.dataset.code);
    }
  });

  document.addEventListener('keydown',event=>{
    if(event.key!=='Enter'&&event.key!==' ')return;
    const card=cardFromTarget(event.target);
    if(!card||event.target!==card)return;
    event.preventDefault();
    openCode(card.dataset.code);
  });
})();
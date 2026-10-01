(()=>{
  if(window.__DOGSON_CARD_OPEN_V1752__) return;
  window.__DOGSON_CARD_OPEN_V1752__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const INTERACTIVE='button,a,input,select,textarea,summary,[role="button"],[data-portfolio-edit],[data-portfolio-save],[data-portfolio-remove],[data-peer-open],[data-peer-close]';

  function cardDetails(card){return $(':scope>.dogson-card-details',card)}
  function setOpen(details,open){
    if(!details)return;
    details.open=!!open;
    const summary=$(':scope>summary',details);
    if(summary)summary.setAttribute('aria-expanded',details.open?'true':'false');
  }
  function toggleCard(card){
    const d=cardDetails(card);if(!d)return false;
    setOpen(d,!d.open);
    setTimeout(()=>d.scrollIntoView({behavior:'smooth',block:'nearest'}),20);
    return true;
  }
  function rowFor(code,view){
    try{
      const pools=[];
      if(view==='close')pools.push(Array.isArray(closeRows)?closeRows:[]);
      else if(view==='daytrade')pools.push(Array.isArray(daytradeRows)?daytradeRows:[],Array.isArray(intraRows)?intraRows:[]);
      else pools.push(Array.isArray(intraRows)?intraRows:[],Array.isArray(closeRows)?closeRows:[]);
      for(const pool of pools){const row=pool.find(r=>String(r?.code||'')===String(code));if(row)return row}
    }catch{}
    return null;
  }
  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function fallbackPeer(peer){
    if($('#peerPeekBack')||typeof showPeerPeek!=='function')return;
    const code=String(peer?.dataset?.code||'');if(!code)return;
    const view=String(peer?.dataset?.flowView||modeNow());
    const row=rowFor(code,view);if(!row)return;
    let oldRows,changed=false;
    try{
      if(typeof rows!=='undefined'){oldRows=rows;rows=[row];changed=true}
      showPeerPeek(code);
    }catch(err){console.warn('Dogson peer fallback failed',err)}
    finally{if(changed)try{rows=oldRows}catch{}}
  }

  function installStyle(){
    if($('#dogsonCardOpenStyle1752'))return;
    const s=document.createElement('style');s.id='dogsonCardOpenStyle1752';s.textContent=`
      #cards .card>.top,#cards .card>.dogson-card-brief{cursor:pointer;touch-action:manipulation;-webkit-tap-highlight-color:transparent}
      #cards .dogson-card-details>summary{touch-action:manipulation;-webkit-tap-highlight-color:transparent;user-select:none;-webkit-user-select:none}
      #cards .card.dogson-card-open-ready-v1752>.top:active,#cards .card.dogson-card-open-ready-v1752>.dogson-card-brief:active{opacity:.88}
    `;document.head.appendChild(s);
  }
  function markCards(){
    $$('#cards .card').forEach(card=>{
      card.classList.add('dogson-card-open-ready-v1752');
      const d=cardDetails(card);if(!d)return;
      const s=$(':scope>summary',d);if(s)s.setAttribute('aria-expanded',d.open?'true':'false');
      if(d.dataset.dogsonOpenSync1752!=='1'){
        d.dataset.dogsonOpenSync1752='1';
        d.addEventListener('toggle',()=>{const x=$(':scope>summary',d);if(x)x.setAttribute('aria-expanded',d.open?'true':'false')});
      }
    });
  }

  function boot(){
    installStyle();markCards();
    const root=$('#cards');
    if(root)new MutationObserver(()=>setTimeout(markCards,20)).observe(root,{subtree:true,childList:true});

    document.addEventListener('click',e=>{
      const peer=e.target?.closest?.('.peerlink[data-code]');
      if(peer){setTimeout(()=>fallbackPeer(peer),0);return}

      const card=e.target?.closest?.('#cards .card');if(!card)return;
      if(e.target?.closest?.(INTERACTIVE))return;
      if(e.target?.closest?.('.dogson-quick-detail-back,#peerPeekBack,#portfolioEditBack'))return;
      const top=e.target?.closest?.(':scope>.top,:scope>.dogson-card-brief');
      if(!top&&e.target!==card)return;
      e.preventDefault();
      toggleCard(card);
    });

    setTimeout(markCards,180);setTimeout(markCards,700);
  }

  window.DOGSON_CARD_OPEN_V1752={toggle:code=>{const card=$(`#cards .card[data-code="${CSS.escape(String(code))}"]`);return card?toggleCard(card):false}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

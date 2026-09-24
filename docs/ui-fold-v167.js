(()=>{
  if(window.__DOGSON_FOLD_V167__) return;
  window.__DOGSON_FOLD_V167__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const openState=new Map();
  let busy=false,timer=null;

  function key(card){
    return String(card?.dataset?.code||$('.code',card)?.textContent||'').trim();
  }

  function isPublic(node){
    if(!node?.classList)return false;
    return node.classList.contains('top') ||
      node.classList.contains('dogson-action-strip-v164') ||
      node.classList.contains('dogson-card-brief') ||
      node.classList.contains('livequote') ||
      node.classList.contains('dogson-portfolio-addon-v166') ||
      node.classList.contains('dogson-key-reasons') ||
      node.classList.contains('dogson-card-details');
  }

  function buttonText(details){
    const s=$(':scope>summary',details);if(!s)return;
    s.textContent=details.open?'收合分析 ↑':'▥ 展開分析 ›';
  }

  function bind(details,card){
    if(details.dataset.v167Bound==='1')return;
    details.dataset.v167Bound='1';
    details.addEventListener('toggle',()=>{
      const k=key(card);if(k)openState.set(k,details.open);
      buttonText(details);
    });
  }

  function ensureDetails(card){
    let details=$(':scope>.dogson-card-details',card);
    const k=key(card);

    if(!details){
      details=document.createElement('details');
      details.className='dogson-card-details dogson-fold-v167';
      details.innerHTML='<summary>▥ 展開分析 ›</summary><div class="dogson-card-details-body"></div>';
      details.open=openState.get(k)===true;
      card.appendChild(details);
    }else if(openState.has(k)){
      details.open=openState.get(k)===true;
    }else{
      openState.set(k,!!details.open);
    }

    const body=$(':scope>.dogson-card-details-body',details);
    if(!body)return details;

    [...card.children].forEach(node=>{
      if(node===details||isPublic(node))return;
      body.appendChild(node);
    });

    bind(details,card);
    buttonText(details);
    return details;
  }

  function reorder(card,details){
    const order=[
      $('.top',card),
      $('.dogson-action-strip-v164',card),
      $('.dogson-card-brief',card),
      $('.livequote',card),
      $('.dogson-portfolio-addon-v166',card),
      $('.dogson-key-reasons',card),
      details
    ].filter(Boolean);
    const children=[...card.children];
    const same=children.length===order.length&&order.every((node,i)=>children[i]===node);
    if(!same)order.forEach(node=>card.appendChild(node));
  }

  function card(card){
    const details=ensureDetails(card);
    reorder(card,details);
  }

  function run(){
    if(busy)return;busy=true;
    try{$$('#cards .card').forEach(card)}finally{busy=false}
  }
  function schedule(){if(busy)return;clearTimeout(timer);timer=setTimeout(run,55)}
  function start(){
    run();
    const root=$('#cards');
    const obs=new MutationObserver(schedule);
    if(root)obs.observe(root,{subtree:true,childList:true});
    setTimeout(run,180);setTimeout(run,650);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

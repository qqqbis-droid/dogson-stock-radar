// Stock-card interaction bridge.
// app.js remains the only card renderer; stock-detail-renderer.js remains the only
// stock-detail writer. This module only forwards a deliberate card tap into the
// canonical radar:open-stock event so the two renderers stay decoupled.
(function(){
  function interactiveTarget(target){
    return Boolean(target?.closest?.('button,a,input,select,textarea,summary,label,[role="button"]'));
  }

  document.addEventListener('click',function(event){
    const card=event.target?.closest?.('#cards .card[data-code]');
    if(!card||interactiveTarget(event.target))return;
    const code=String(card.dataset.code||'').trim();
    if(!code)return;
    event.preventDefault();
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code}}));
  });
})();

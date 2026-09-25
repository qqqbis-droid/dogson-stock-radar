(()=>{
  if(window.__DOGSON_LOAD_MORE_V1681__) return;
  window.__DOGSON_LOAD_MORE_V1681__ = true;

  const BUTTON_ID='dogsonLoadMore';
  let observer=null;

  function prepareButton(){
    const b=document.getElementById(BUTTON_ID);
    if(!b) return null;

    // redesign-v160 owns the paging counter in a closure. Preserve that exact
    // handler, then invoke it from a capture listener so Safari/touch layers
    // cannot swallow the tap before the button reaches its onclick handler.
    if(!b.__dogsonOriginalLoadMore && typeof b.onclick==='function'){
      b.__dogsonOriginalLoadMore=b.onclick;
      b.onclick=null;
    }

    b.type='button';
    b.style.position='relative';
    b.style.zIndex='20';
    b.style.pointerEvents='auto';
    b.style.touchAction='manipulation';
    b.setAttribute('aria-label','顯示更多股票');
    return b;
  }

  function activate(e,b){
    const fn=b.__dogsonOriginalLoadMore;
    if(typeof fn!=='function') return false;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    fn.call(b,e);
    return true;
  }

  // Capture first: this is intentionally ahead of later card/detail handlers.
  document.addEventListener('click',e=>{
    const b=e.target?.closest?.('#'+BUTTON_ID);
    if(!b) return;
    prepareButton();
    activate(e,b);
  },true);

  // Keep the handler repaired when scans/filters rebuild the result area.
  function watch(){
    prepareButton();
    if(observer||!document.body) return;
    observer=new MutationObserver(()=>prepareButton());
    observer.observe(document.body,{subtree:true,childList:true});
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',watch,{once:true});
  }else{
    watch();
  }
  setTimeout(prepareButton,250);
  setTimeout(prepareButton,900);
})();

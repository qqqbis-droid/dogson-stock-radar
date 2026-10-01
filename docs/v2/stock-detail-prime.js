(function(){
  function openImmediately(code){
    const view=document.querySelector('.tab.active')?.dataset?.view||'intraday';
    if(view==='portfolio')return;

    const dialog=document.getElementById('detailDialog');
    const title=document.getElementById('detailTitle');
    const body=document.getElementById('detailBody');
    if(!dialog||!title||!body)return;

    title.textContent=`${String(code||'').trim()} 個股詳情`;
    body.textContent='讀取個股詳情…';

    if(dialog.open)return;
    try{
      dialog.showModal();
    }catch(err){
      // Older / stricter mobile WebKit fallback: make the dialog visible even
      // if modal promotion fails. The canonical renderer will still fill it.
      dialog.setAttribute('open','');
      dialog.classList.add('detail-dialog-fallback');
      console.warn('stock-detail-prime fallback',err);
    }
  }

  document.addEventListener('radar:open-stock',event=>{
    const code=String(event.detail?.code||'').trim();
    if(code)openImmediately(code);
  });
})();

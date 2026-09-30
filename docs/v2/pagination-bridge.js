(()=>{
  function init(){
    const btn=document.getElementById('loadMore');
    const count=document.getElementById('countText');
    const search=document.getElementById('searchInput');
    const stage=document.getElementById('stageFilter');
    const action=document.getElementById('actionFilter');
    if(!btn||!count)return;
    const sync=()=>{
      const active=document.querySelector('.tab.active')?.dataset.view;
      if(active==='portfolio')return;
      const text=(count.textContent||'').trim();
      const m=text.match(/^(\d+)\/(\d+)\s*檔$/);
      if(!m)return;
      const shown=Number(m[1]),total=Number(m[2]);
      const deep=Boolean(search?.value.trim()||stage?.value||action?.value);
      if(!deep&&shown===15&&total===15){
        btn.classList.remove('hidden');
        btn.textContent='查看更多全部候選';
        btn.dataset.lazyIndexBridge='1';
      }else if(total>shown){
        btn.classList.remove('hidden');
        btn.textContent='查看更多';
        delete btn.dataset.lazyIndexBridge;
      }
    };
    new MutationObserver(sync).observe(count,{childList:true,characterData:true,subtree:true});
    document.getElementById('tabs')?.addEventListener('click',()=>setTimeout(sync,0));
    [search,stage,action].forEach(el=>el?.addEventListener('input',()=>setTimeout(sync,0)));
    setTimeout(sync,0);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();

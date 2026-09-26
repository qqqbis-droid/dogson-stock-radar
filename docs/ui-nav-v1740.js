(()=>{
  if(window.__DOGSON_NAV_V1740__) return;
  window.__DOGSON_NAV_V1740__ = true;

  function installStyle(){
    if(document.getElementById('dogson-nav-style-v1740')) return;
    const s=document.createElement('style');
    s.id='dogson-nav-style-v1740';
    s.textContent=`
      #dogsonViewNav .dogson-view-main{
        display:grid!important;
        grid-template-columns:repeat(4,minmax(0,1fr))!important;
        width:100%;
      }
      #dogsonViewNav .dogson-view-main>button{
        min-width:0;
        white-space:nowrap;
        text-align:center;
      }
    `;
    document.head.appendChild(s);
  }

  function setButton(btn,label,title){
    if(btn.textContent!==label) btn.textContent=label;
    if(btn.title!==title) btn.title=title;
  }

  function patchNav(){
    installStyle();
    const main=document.querySelector('#dogsonViewNav .dogson-view-main');
    if(!main) return false;

    const intraday=main.querySelector('[data-v="find"]');
    const close=main.querySelector('[data-v="close"]');
    const portfolio=main.querySelector('[data-v="portfolio"]');
    const daytrade=main.querySelector('[data-v="daytrade"]');
    if(!intraday||!close||!portfolio||!daytrade) return false;

    setButton(intraday,'盤中','盤中波段');
    setButton(close,'盤後','盤後波段');
    setButton(portfolio,'庫存','我的庫存');
    setButton(daytrade,'當沖','當沖模式');

    const desired=[intraday,close,portfolio,daytrade];
    const current=[...main.querySelectorAll(':scope > button[data-v]')];
    const ordered=current.length===desired.length&&desired.every((btn,i)=>current[i]===btn);
    if(!ordered) desired.forEach(btn=>main.appendChild(btn));

    if(main.dataset.navVersion!=='1740') main.dataset.navVersion='1740';
    return true;
  }

  let timer=null;
  function schedule(){
    clearTimeout(timer);
    timer=setTimeout(patchNav,30);
  }

  function boot(){
    patchNav();
    const root=document.querySelector('.wrap')||document.body;
    if(root) new MutationObserver(schedule).observe(root,{childList:true,subtree:true});
    document.addEventListener('click',e=>{
      if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')) setTimeout(patchNav,40);
    });
    setTimeout(patchNav,250);
    setTimeout(patchNav,1000);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();

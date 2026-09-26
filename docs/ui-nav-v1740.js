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

  function patchNav(){
    installStyle();
    const main=document.querySelector('#dogsonViewNav .dogson-view-main');
    if(!main) return false;

    const intraday=main.querySelector('[data-v="find"]');
    const close=main.querySelector('[data-v="close"]');
    const portfolio=main.querySelector('[data-v="portfolio"]');
    const daytrade=main.querySelector('[data-v="daytrade"]');
    if(!intraday||!close||!portfolio||!daytrade) return false;

    intraday.textContent='盤中';
    intraday.title='盤中波段';
    close.textContent='盤後';
    close.title='盤後波段';
    portfolio.textContent='庫存';
    portfolio.title='我的庫存';
    daytrade.textContent='當沖';
    daytrade.title='當沖模式';

    [intraday,close,portfolio,daytrade].forEach(btn=>main.appendChild(btn));
    main.dataset.navVersion='1740';
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

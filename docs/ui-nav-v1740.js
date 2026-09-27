(()=>{
  if(window.__DOGSON_NAV_V1741__) return;
  window.__DOGSON_NAV_V1741__ = true;

  function installStyle(){
    const old=document.getElementById('dogson-nav-style-v1740');
    if(old) old.remove();
    if(document.getElementById('dogson-nav-style-v1741')) return;
    const s=document.createElement('style');
    s.id='dogson-nav-style-v1741';
    s.textContent=`
      #dogsonViewNav.dogson-view-nav{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) 48px!important;
        gap:10px!important;
        align-items:center!important;
        padding:0!important;
        background:transparent!important;
        border:0!important;
        border-radius:0!important;
        box-shadow:none!important;
        backdrop-filter:none!important;
        -webkit-backdrop-filter:none!important;
        overflow:visible!important;
      }
      #dogsonViewNav .dogson-view-main{
        display:grid!important;
        grid-template-columns:repeat(4,minmax(0,1fr))!important;
        gap:4px!important;
        width:100%!important;
        min-width:0!important;
        padding:4px!important;
        margin:0!important;
        box-sizing:border-box!important;
        position:relative!important;
        overflow:hidden!important;
        background:#eef2ef!important;
        border:1px solid #dfe6e1!important;
        border-radius:20px!important;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.8)!important;
      }
      #dogsonViewNav .dogson-view-main::before,
      #dogsonViewNav .dogson-view-main::after,
      #dogsonViewNav .dogson-view-main>button::before,
      #dogsonViewNav .dogson-view-main>button::after{
        content:none!important;
        display:none!important;
      }
      #dogsonViewNav .dogson-view-main>button{
        appearance:none!important;
        -webkit-appearance:none!important;
        min-width:0!important;
        min-height:48px!important;
        margin:0!important;
        padding:0 6px!important;
        border:0!important;
        border-radius:16px!important;
        background:transparent!important;
        background-image:none!important;
        box-shadow:none!important;
        color:#56665f!important;
        opacity:1!important;
        white-space:nowrap!important;
        text-align:center!important;
        font-size:14px!important;
        font-weight:800!important;
        line-height:1!important;
        letter-spacing:.02em!important;
        position:relative!important;
        z-index:1!important;
        transform:none!important;
        transition:background-color .18s ease,color .18s ease,box-shadow .18s ease,transform .12s ease!important;
      }
      #dogsonViewNav .dogson-view-main>button.active{
        background:#2f7865!important;
        background-image:none!important;
        color:#fff!important;
        box-shadow:0 2px 8px rgba(34,86,71,.20),inset 0 1px 0 rgba(255,255,255,.10)!important;
      }
      #dogsonViewNav .dogson-view-main>button:not(.active):active{
        background:#e2e9e5!important;
        transform:scale(.98)!important;
      }
      #dogsonViewNav .dogson-view-main>button:focus-visible{
        outline:2px solid rgba(47,120,101,.35)!important;
        outline-offset:-2px!important;
      }
      #dogsonViewNav .dogson-theme-toggle{
        appearance:none!important;
        -webkit-appearance:none!important;
        width:48px!important;
        height:56px!important;
        min-width:48px!important;
        flex:0 0 48px!important;
        margin:0!important;
        padding:0!important;
        display:grid!important;
        place-items:center!important;
        border:1px solid #dfe6e1!important;
        border-radius:18px!important;
        background:#fff!important;
        color:#52665e!important;
        box-shadow:0 2px 8px rgba(34,51,43,.05)!important;
        font-size:20px!important;
        font-weight:700!important;
        line-height:1!important;
      }
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main{
        background:#252b28!important;
        border-color:#39423d!important;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
      }
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button{
        color:#aeb9b3!important;
      }
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button.active{
        background:#3a806d!important;
        color:#fff!important;
        box-shadow:0 2px 8px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.07)!important;
      }
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button:not(.active):active{
        background:#303733!important;
      }
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-theme-toggle{
        background:#252b28!important;
        border-color:#39423d!important;
        color:#e3ebe6!important;
        box-shadow:0 2px 8px rgba(0,0,0,.16)!important;
      }
      @media(max-width:720px){
        #dogsonViewNav.dogson-view-nav{
          grid-template-columns:minmax(0,1fr) 46px!important;
          gap:8px!important;
        }
        #dogsonViewNav .dogson-view-main{
          padding:4px!important;
          gap:3px!important;
          border-radius:19px!important;
        }
        #dogsonViewNav .dogson-view-main>button{
          min-height:46px!important;
          padding:0 3px!important;
          border-radius:15px!important;
          font-size:13px!important;
        }
        #dogsonViewNav .dogson-theme-toggle{
          width:46px!important;
          height:54px!important;
          min-width:46px!important;
          flex-basis:46px!important;
          border-radius:17px!important;
          font-size:19px!important;
        }
      }
    `;
    document.head.appendChild(s);
  }

  function setButton(btn,label,title){
    if(btn.textContent!==label) btn.textContent=label;
    if(btn.title!==title) btn.title=title;
    btn.setAttribute('role','tab');
    btn.setAttribute('aria-selected',btn.classList.contains('active')?'true':'false');
  }

  function patchNav(){
    installStyle();
    const nav=document.getElementById('dogsonViewNav');
    const main=nav?.querySelector('.dogson-view-main');
    if(!main) return false;

    const intraday=main.querySelector('[data-v="find"]');
    const close=main.querySelector('[data-v="close"]');
    const portfolio=main.querySelector('[data-v="portfolio"]');
    const daytrade=main.querySelector('[data-v="daytrade"]');
    if(!intraday||!close||!portfolio||!daytrade) return false;

    nav.setAttribute('aria-label','交易功能');
    main.setAttribute('role','tablist');
    setButton(intraday,'盤中','盤中波段');
    setButton(close,'盤後','盤後波段');
    setButton(portfolio,'庫存','我的庫存');
    setButton(daytrade,'當沖','當沖模式');

    const desired=[intraday,close,portfolio,daytrade];
    const current=[...main.querySelectorAll(':scope > button[data-v]')];
    const ordered=current.length===desired.length&&desired.every((btn,i)=>current[i]===btn);
    if(!ordered) desired.forEach(btn=>main.appendChild(btn));

    desired.forEach(btn=>btn.setAttribute('aria-selected',btn.classList.contains('active')?'true':'false'));
    main.dataset.navVersion='1741';
    return true;
  }

  let timer=null;
  function schedule(){
    clearTimeout(timer);
    timer=setTimeout(patchNav,25);
  }

  function boot(){
    patchNav();
    const root=document.querySelector('.wrap')||document.body;
    if(root) new MutationObserver(schedule).observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',e=>{
      if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')) setTimeout(patchNav,35);
    });
    setTimeout(patchNav,200);
    setTimeout(patchNav,800);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();

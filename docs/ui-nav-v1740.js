(()=>{
  if(window.__DOGSON_NAV_V1742__) return;
  window.__DOGSON_NAV_V1742__ = true;

  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function installStyle(){
    document.getElementById('dogson-nav-style-v1740')?.remove();
    document.getElementById('dogson-nav-style-v1741')?.remove();
    if(document.getElementById('dogson-nav-style-v1742')) return;
    const s=document.createElement('style');
    s.id='dogson-nav-style-v1742';
    s.textContent=`
      .wrap>header.dogson-header-v1742{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) 118px!important;
        column-gap:10px!important;
        align-items:stretch!important;
        margin:4px 2px 10px!important;
      }
      .wrap>header.dogson-header-v1742>div:first-child{
        min-width:0!important;
        display:flex!important;
        flex-direction:column!important;
        justify-content:center!important;
      }
      .wrap>header.dogson-header-v1742 h1{
        margin:0!important;
        white-space:nowrap!important;
        overflow:visible!important;
        text-overflow:clip!important;
        line-height:1.18!important;
      }
      .wrap>header.dogson-header-v1742 .sub{
        margin-top:4px!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
      }
      .wrap>header.dogson-header-v1742 #status.dogson-status-v1742{
        width:118px!important;
        min-width:118px!important;
        min-height:52px!important;
        box-sizing:border-box!important;
        margin:0!important;
        padding:7px 9px!important;
        border-radius:12px!important;
        display:flex!important;
        flex-direction:column!important;
        justify-content:center!important;
        gap:2px!important;
        font-size:11px!important;
        font-weight:800!important;
        line-height:1.25!important;
        letter-spacing:0!important;
        white-space:normal!important;
      }
      .wrap>header.dogson-header-v1742 #status.dogson-status-two{
        align-items:flex-start!important;
        text-align:left!important;
      }
      .wrap>header.dogson-header-v1742 #status.dogson-status-single{
        align-items:center!important;
        text-align:center!important;
      }
      .wrap>header.dogson-header-v1742 #status .dogson-status-line{
        display:block!important;
        width:100%!important;
        white-space:nowrap!important;
      }

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
        .wrap>header.dogson-header-v1742{
          grid-template-columns:minmax(0,1fr) 108px!important;
          column-gap:8px!important;
        }
        .wrap>header.dogson-header-v1742 #status.dogson-status-v1742{
          width:108px!important;
          min-width:108px!important;
          min-height:50px!important;
          padding:6px 8px!important;
          font-size:10.5px!important;
        }
        .wrap>header.dogson-header-v1742 h1{
          font-size:22px!important;
        }
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
      @media(max-width:360px){
        .wrap>header.dogson-header-v1742{
          grid-template-columns:minmax(0,1fr) 102px!important;
          column-gap:6px!important;
        }
        .wrap>header.dogson-header-v1742 #status.dogson-status-v1742{
          width:102px!important;
          min-width:102px!important;
          padding-left:7px!important;
          padding-right:7px!important;
          font-size:10px!important;
        }
        .wrap>header.dogson-header-v1742 h1{font-size:20px!important}
        .wrap>header.dogson-header-v1742 .sub{font-size:11px!important}
      }
    `;
    document.head.appendChild(s);
  }

  function formatStatus(){
    const header=document.querySelector('.wrap>header');
    const status=document.getElementById('status');
    if(!header||!status) return false;
    header.classList.add('dogson-header-v1742');
    status.classList.add('dogson-status-v1742');

    let raw;
    const hasLines=!!status.querySelector('.dogson-status-line');
    if(hasLines) raw=status.dataset.dogsonStatusRaw||'';
    else raw=(status.textContent||'').replace(/\s+/g,' ').trim();
    if(!raw) return true;

    const parts=raw.split(/[｜|]/).map(x=>x.trim()).filter(Boolean);
    if(parts.length>=2){
      const first=parts.shift();
      const second=parts.join('｜').replace(/5分K\s*結構/g,'5分K').trim();
      const displayRaw=`${first}｜${second}`;
      if(status.dataset.dogsonStatusDisplay!==displayRaw||!hasLines){
        status.innerHTML=`<span class="dogson-status-line">${esc(first)}｜</span><span class="dogson-status-line">${esc(second)}</span>`;
        status.dataset.dogsonStatusDisplay=displayRaw;
      }
      status.dataset.dogsonStatusRaw=raw;
      status.classList.add('dogson-status-two');
      status.classList.remove('dogson-status-single');
    }else{
      if(hasLines||status.textContent.trim()!==raw) status.textContent=raw;
      status.dataset.dogsonStatusRaw=raw;
      status.dataset.dogsonStatusDisplay=raw;
      status.classList.add('dogson-status-single');
      status.classList.remove('dogson-status-two');
    }
    return true;
  }

  function setButton(btn,label,title){
    if(btn.textContent!==label) btn.textContent=label;
    if(btn.title!==title) btn.title=title;
    btn.setAttribute('role','tab');
    btn.setAttribute('aria-selected',btn.classList.contains('active')?'true':'false');
  }

  function patchNav(){
    installStyle();
    formatStatus();
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
    main.dataset.navVersion='1742';
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
    if(root) new MutationObserver(mutations=>{
      const status=document.getElementById('status');
      const externalStatusChange=mutations.some(m=>m.target===status&&!status?.querySelector?.('.dogson-status-line'));
      if(externalStatusChange) status.dataset.dogsonStatusRaw=(status.textContent||'').replace(/\s+/g,' ').trim();
      schedule();
    }).observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',e=>{
      if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')) setTimeout(patchNav,35);
    });
    setTimeout(patchNav,200);
    setTimeout(patchNav,800);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();

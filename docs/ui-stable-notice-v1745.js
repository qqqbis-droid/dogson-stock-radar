(()=>{
  if(window.__DOGSON_STABLE_NOTICE_V1745__) return;
  window.__DOGSON_STABLE_NOTICE_V1745__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const shortDate=v=>{
    const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);
    return m?`${Number(m[1])}/${Number(m[2])}`:'';
  };
  const modeNow=()=>{try{return mode||'intraday'}catch{return document.documentElement.dataset.dogsonPage||'intraday'}};
  const portfolioView=()=>{try{return !!portfolioOnly}catch{return document.documentElement.dataset.dogsonPage==='portfolio'}};

  function installStyle(){
    if($('#dogson-stable-notice-style-v1745')) return;
    const s=document.createElement('style');
    s.id='dogson-stable-notice-style-v1745';
    s.textContent=`
      /* Legacy safety notice keeps calculating state, but no longer owns visible UI. */
      #dogsonAccuracyGuardV1702{display:none!important}
      #dogsonStableNoticeV1745{
        margin:4px 0 10px!important;
        padding:0 10px!important;
        height:30px!important;
        min-height:30px!important;
        max-height:30px!important;
        box-sizing:border-box!important;
        border:1px solid #ead9a9!important;
        border-radius:10px!important;
        background:#fff8e8!important;
        color:#6f5718!important;
        display:flex!important;
        align-items:center!important;
        overflow:hidden!important;
        white-space:nowrap!important;
        box-shadow:none!important;
        font-size:10px!important;
        font-weight:850!important;
        line-height:1!important;
      }
      #dogsonStableNoticeV1745.bad{
        border-color:#efc5ca!important;
        background:#fff0f2!important;
        color:#8e303a!important;
      }
      #dogsonStableNoticeV1745 .dogson-stable-notice-text{
        display:block!important;
        width:100%!important;
        min-width:0!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }
      html[data-dogson-theme="dark"] #dogsonStableNoticeV1745{
        background:#332c1b!important;
        border-color:#5a4b25!important;
        color:#f0d98e!important;
      }
      html[data-dogson-theme="dark"] #dogsonStableNoticeV1745.bad{
        background:#352126!important;
        border-color:#63343b!important;
        color:#ffb8c0!important;
      }
    `;
    document.head.appendChild(s);
  }

  function spec(){
    const snap=window.DOGSON_DATA_TRUTH_V1700;
    if(!snap) return null;
    const dates=snap.dates||{};
    const m=modeNow(),p=portfolioView();
    const live=window.DOGSON_INTRADAY_LIVE_READY===true||snap.operational?.liveReady===true;
    const actionable=window.DOGSON_DAYTRADE_ACTIONABLE===true||snap.operational?.dayActionable===true;

    if(m==='intraday'&&!p&&!live){
      const d=shortDate(dates.close||dates.market||snap.latest);
      return {tone:'warn',text:`🛡 非即時盤中｜候選股使用 ${d||'最近交易日'} 完整盤後資料`};
    }
    if(m==='intraday'&&p&&!live){
      const d=shortDate(dates.close||dates.market||snap.latest);
      return {tone:'warn',text:`🛡 非即時庫存｜使用 ${d||'最近交易日'} 完整盤後結構`};
    }
    if(m==='daytrade'&&!actionable){
      return {tone:'bad',text:'🎯 當沖目前不可執行｜即時條件未通過，歷史資料僅供回顧'};
    }
    return null;
  }

  function render(){
    installStyle();
    const x=spec();
    let el=$('#dogsonStableNoticeV1745');
    if(!x){el?.remove();return}

    const anchor=$('#dogsonMissionV1700')||$('#dogsonViewNav');
    if(!anchor) return;
    if(!el){
      el=document.createElement('aside');
      el.id='dogsonStableNoticeV1745';
      el.innerHTML='<span class="dogson-stable-notice-text"></span>';
      anchor.insertAdjacentElement('afterend',el);
    }else if(el.previousElementSibling!==anchor){
      anchor.insertAdjacentElement('afterend',el);
    }

    el.classList.toggle('bad',x.tone==='bad');
    const text=$('.dogson-stable-notice-text',el);
    if(text&&text.textContent!==x.text) text.textContent=x.text;
  }

  function boot(){
    installStyle();
    render();
    window.addEventListener('dogson:data-truth',()=>setTimeout(render,10));
    window.addEventListener('dogson:actionability',()=>setTimeout(render,10));
    window.addEventListener('dogson:freshness',()=>setTimeout(render,10));
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly'))setTimeout(render,40)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(render,20)});
    setTimeout(render,250);
    setTimeout(render,900);
    setInterval(()=>{if(!document.hidden)render()},60000);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();

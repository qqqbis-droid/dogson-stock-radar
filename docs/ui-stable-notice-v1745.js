(()=>{
  if(window.__DOGSON_HEADER_ONLY_STATUS_V1746__) return;
  window.__DOGSON_HEADER_ONLY_STATUS_V1746__=true;

  const $=(s,r=document)=>r.querySelector(s);

  function taipeiClock(){
    try{
      const p={};
      new Intl.DateTimeFormat('en-CA',{
        timeZone:'Asia/Taipei',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
      }).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});
      const minute=Number(p.hour)*60+Number(p.minute);
      const weekday=['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday);
      return {session:weekday&&minute>=535&&minute<=815};
    }catch{return {session:false}}
  }

  function installStyle(){
    if($('#dogson-header-only-status-style-v1746')) return;
    const s=document.createElement('style');
    s.id='dogson-header-only-status-style-v1746';
    s.textContent=`
      /* Data status has one visual owner: the header badge. */
      #dogsonAccuracyGuardV1702,
      #dogsonStableNoticeV1745{
        display:none!important;
      }

      .wrap>header #status.dogson-status-alert-v1746{
        background:#fff8e8!important;
        border-color:#ead9a9!important;
        color:#6f5718!important;
      }
      html[data-dogson-theme="dark"] .wrap>header #status.dogson-status-alert-v1746{
        background:#332c1b!important;
        border-color:#5a4b25!important;
        color:#f0d98e!important;
      }
    `;
    document.head.appendChild(s);
  }

  function sync(){
    installStyle();

    // Remove the newer compact notice entirely. The legacy guard may recreate
    // its own node because it still owns safety logic, but CSS keeps it hidden.
    $('#dogsonStableNoticeV1745')?.remove();

    const status=$('#status');
    if(!status) return;

    const m=(()=>{try{return mode||'intraday'}catch{return document.documentElement.dataset.dogsonPage||'intraday'}})();
    const inSession=taipeiClock().session;
    const live=window.DOGSON_INTRADAY_LIVE_READY===true;
    const dayActionable=window.DOGSON_DAYTRADE_ACTIONABLE===true;

    // Off-hours / weekends using the latest complete close data is normal,
    // not an error. Highlight only when the market should be live but the
    // corresponding real-time layer is unavailable.
    const abnormal=(m==='intraday'&&inSession&&!live)||(m==='daytrade'&&inSession&&!dayActionable);
    status.classList.toggle('dogson-status-alert-v1746',abnormal);
  }

  function boot(){
    sync();
    window.addEventListener('dogson:data-truth',()=>setTimeout(sync,10));
    window.addEventListener('dogson:actionability',()=>setTimeout(sync,10));
    window.addEventListener('dogson:freshness',()=>setTimeout(sync,10));
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly'))setTimeout(sync,40)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(sync,20)});
    setTimeout(sync,250);
    setTimeout(sync,900);
    setInterval(()=>{if(!document.hidden)sync()},60000);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();

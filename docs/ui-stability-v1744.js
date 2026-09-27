(()=>{
  if(window.__DOGSON_STABILITY_V1744__) return;
  window.__DOGSON_STABILITY_V1744__=true;

  const s=document.createElement('style');
  s.id='dogson-stability-style-v1744';
  s.textContent=`
    /* Keep the header footprint fixed even while legacy status renderers refresh. */
    .wrap>header #status{
      height:58px!important;
      min-height:58px!important;
      max-height:58px!important;
      overflow:hidden!important;
      box-sizing:border-box!important;
    }

    /* The safety module may replace its className/innerHTML during refreshes.
       Style by stable ID so it never expands back into the old large card. */
    #dogsonAccuracyGuardV1702{
      margin:4px 0 10px!important;
      padding:0 10px!important;
      height:31px!important;
      min-height:31px!important;
      max-height:31px!important;
      box-sizing:border-box!important;
      border-radius:10px!important;
      box-shadow:none!important;
      display:flex!important;
      align-items:center!important;
      gap:2px!important;
      overflow:hidden!important;
      white-space:nowrap!important;
      line-height:1!important;
    }
    #dogsonAccuracyGuardV1702 .dogson-accuracy-title-v1702{
      display:block!important;
      flex:0 0 auto!important;
      margin:0!important;
      font-size:10.5px!important;
      font-weight:950!important;
      line-height:1!important;
      white-space:nowrap!important;
    }
    #dogsonAccuracyGuardV1702 .dogson-accuracy-text-v1702{
      display:block!important;
      flex:1 1 auto!important;
      min-width:0!important;
      margin:0!important;
      font-size:10px!important;
      line-height:1!important;
      white-space:nowrap!important;
      overflow:hidden!important;
      text-overflow:ellipsis!important;
    }

    @media(max-width:720px){
      .wrap>header #status{
        height:56px!important;
        min-height:56px!important;
        max-height:56px!important;
      }
      #dogsonAccuracyGuardV1702{
        height:30px!important;
        min-height:30px!important;
        max-height:30px!important;
        padding-left:9px!important;
        padding-right:9px!important;
      }
    }
  `;
  document.head.appendChild(s);
})();

(()=>{
  if(window.__DOGSON_CANDIDATE_V1752__) return;
  window.__DOGSON_CANDIDATE_V1752__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();

  const LIMIT=8;
  const QUALITY_MIN=75;
  const POSITION_MIN=65;
  const CHIP_COVERAGE_MIN=60;
  const state={enabled:false};
  let innerRender=null;
  let wrapping=false;
  let syncTimer=null;
  let lastCloseView=false;

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function portfolioNow(){try{return !!portfolioOnly}catch{return false}}
  function isCloseView(){return modeNow()==='close'&&!portfolioNow()}
  function stageOf(r){
    try{return clean(stageKey(r?.category))}catch{return clean(r?.category||r?.stage||'觀察')}
  }
  function qualityOf(r){return num(r?.swing_quality_score??r?.close_score??r?.score)??0}
  function positionOf(r){return num(r?.entry_position_score)??0}
  function confidenceOf(r){
    return num(r?.data_confidence_score??r?.confidence_score??r?.data_confidence??r?.confidence)??0;
  }
  function stagePriority(r){
    const s=stageOf(r);
    if(/剛啟動/.test(s))return 4;
    if(/回踩/.test(s))return 3;
    if(/蓄勢/.test(s))return 2;
    if(/趨勢|持有/.test(s))return 1;
    return 0;
  }
  function liquidEnough(r){
    const s=clean(r?.liquidity_level);
    if(/不足|偏低|低流動|極低|不佳/.test(s))return false;
    return true;
  }
  function eligible(r){
    const st=stageOf(r);
    if(/轉弱|失效|過熱/.test(st))return false;
    if(!/剛啟動|回踩|蓄勢|趨勢|持有/.test(st))return false;
    if(r?.score_reliable===false)return false;
    if(qualityOf(r)<QUALITY_MIN)return false;
    if(positionOf(r)<POSITION_MIN)return false;
    const chip=num(r?.chip_coverage_pct);
    if(chip!==null&&chip<CHIP_COVERAGE_MIN)return false;
    if(!liquidEnough(r))return false;
    return true;
  }
  function candidateRows(source){
    const arr=Array.isArray(source)?source.slice():[];
    return arr.filter(eligible).sort((a,b)=>
      stagePriority(b)-stagePriority(a) ||
      qualityOf(b)-qualityOf(a) ||
      positionOf(b)-positionOf(a) ||
      confidenceOf(b)-confidenceOf(a) ||
      String(a?.code||'').localeCompare(String(b?.code||''),'zh-Hant',{numeric:true})
    ).slice(0,LIMIT);
  }
  function currentCandidates(){
    try{return candidateRows(Array.isArray(closeRows)?closeRows:[])}catch{return[]}
  }

  function installRender(){
    if(typeof render!=='function')return false;
    if(render.__dogsonCandidateV1752)return true;
    innerRender=render;
    const wrapped=function(...args){
      if(wrapping||!state.enabled||!isCloseView())return innerRender.apply(this,args);
      wrapping=true;
      let oldClose,oldRows;
      try{oldClose=closeRows}catch{}
      try{oldRows=rows}catch{}
      const picked=candidateRows(oldClose);
      try{
        try{closeRows=picked}catch{}
        try{if(modeNow()==='close')rows=picked}catch{}
        return innerRender.apply(this,args);
      }finally{
        try{closeRows=oldClose}catch{}
        try{rows=oldRows}catch{}
        wrapping=false;
        scheduleSync();
      }
    };
    Object.keys(innerRender).forEach(k=>{try{wrapped[k]=innerRender[k]}catch{}});
    wrapped.__dogsonCandidateV1752=true;
    wrapped.__dogsonCandidateInner=innerRender;
    render=wrapped;
    return true;
  }

  function setEnabled(v,{renderNow=true,scroll=false}={}){
    const next=!!v;
    if(state.enabled===next){syncUi();return}
    state.enabled=next;
    if(renderNow)try{render()}catch{}
    syncUi();
    if(scroll)setTimeout(()=>($('#cards')||$('.meta'))?.scrollIntoView({behavior:'smooth',block:'start'}),70);
  }

  function ensureUi(){
    let box=$('#dogsonNextDayV1752');
    const quick=$('#dogsonQuickFilters');
    const overview=$('#dogsonOverviewV160');
    if(!box){
      box=document.createElement('section');
      box.id='dogsonNextDayV1752';
      box.className='dogson-nextday-v1752';
      box.innerHTML='<button type="button" class="dogson-nextday-main-v1752" data-nextday-toggle="1"><span class="dogson-nextday-kicker-v1752">⭐ 明日候選</span><b class="dogson-nextday-count-v1752">0 檔</b><small>品質 ≥75・位置 ≥65・最多 8 檔</small></button><button type="button" class="dogson-nextday-all-v1752" data-nextday-all="1">查看全部</button>';
    }
    const anchor=quick||overview;
    if(anchor&&box.parentElement!==anchor.parentElement)anchor.parentElement?.insertBefore(box,quick||overview?.nextSibling||null);
    else if(anchor&&box.nextElementSibling!==quick&&quick)quick.before(box);
    return box;
  }

  function installStyle(){
    if($('#dogsonNextDayStyle1752'))return;
    const s=document.createElement('style');s.id='dogsonNextDayStyle1752';s.textContent=`
      #dogsonNextDayV1752{display:none;margin:8px 0 7px;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:stretch}
      html[data-dogson-page="close"] #dogsonNextDayV1752{display:grid}
      .dogson-nextday-main-v1752,.dogson-nextday-all-v1752{appearance:none;-webkit-appearance:none;border-radius:13px;font:inherit;touch-action:manipulation}
      .dogson-nextday-main-v1752{display:grid;grid-template-columns:auto auto;grid-template-areas:'k c' 's s';justify-content:space-between;align-items:center;gap:2px 10px;padding:9px 11px;border:1px solid #cddbd3;background:#fff;color:#31483e;text-align:left}
      .dogson-nextday-main-v1752.active{background:#e7f2ec;border-color:#8db6a3;box-shadow:inset 0 0 0 1px #a9c7b7}
      .dogson-nextday-kicker-v1752{grid-area:k;font-size:12px;font-weight:950}.dogson-nextday-count-v1752{grid-area:c;font-size:13px;color:#2f6c58}.dogson-nextday-main-v1752 small{grid-area:s;font-size:9px;color:#7a8881}
      .dogson-nextday-all-v1752{padding:0 11px;border:1px solid #dbe4df;background:#f7f9f7;color:#5f7168;font-size:10px;font-weight:850;white-space:nowrap}
      .dogson-nextday-all-v1752.active{background:#315f52;color:#fff;border-color:#315f52}
      html[data-dogson-theme="dark"] .dogson-nextday-main-v1752{background:#252b28;border-color:#39443e;color:#e7eee9}html[data-dogson-theme="dark"] .dogson-nextday-main-v1752.active{background:#29453b;border-color:#527e6d}html[data-dogson-theme="dark"] .dogson-nextday-count-v1752{color:#a9ddc8}html[data-dogson-theme="dark"] .dogson-nextday-main-v1752 small{color:#9ba7a1}html[data-dogson-theme="dark"] .dogson-nextday-all-v1752{background:#252b28;border-color:#39443e;color:#bec9c3}
    `;document.head.appendChild(s);
  }

  function syncUi(){
    installStyle();
    const box=ensureUi();if(!box)return;
    const count=currentCandidates().length;
    $('.dogson-nextday-count-v1752',box).textContent=`${count} 檔`;
    const main=$('[data-nextday-toggle]',box),all=$('[data-nextday-all]',box);
    main?.classList.toggle('active',state.enabled&&isCloseView());
    main?.setAttribute('aria-pressed',state.enabled&&isCloseView()?'true':'false');
    all?.classList.toggle('active',!state.enabled&&isCloseView());
    box.hidden=!isCloseView();
  }
  function scheduleSync(){clearTimeout(syncTimer);syncTimer=setTimeout(sync,45)}
  function sync(){
    const close=isCloseView();
    if(close&&!lastCloseView){
      state.enabled=true;
      setTimeout(()=>{try{render()}catch{}},0);
    }else if(!close&&lastCloseView){
      state.enabled=false;
    }
    lastCloseView=close;
    syncUi();
  }

  function boot(){
    installStyle();
    let tries=0;const t=setInterval(()=>{tries++;if(installRender()||tries>100){clearInterval(t);sync();}},40);
    document.addEventListener('click',e=>{
      const toggle=e.target?.closest?.('[data-nextday-toggle]');
      if(toggle){e.preventDefault();setEnabled(!state.enabled,{scroll:true});return}
      const all=e.target?.closest?.('[data-nextday-all]');
      if(all){e.preventDefault();setEnabled(false,{scroll:true});return}
      if(e.target?.closest?.('[data-dogson-clear]')&&isCloseView())setEnabled(false,{renderNow:false});
      if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(sync,90);
    },true);
    window.addEventListener('dogson:data-ready',()=>setTimeout(()=>{syncUi();if(state.enabled&&isCloseView())try{render()}catch{}},30));
    window.addEventListener('dogson:data-truth',()=>setTimeout(syncUi,30));
    const root=$('.wrap')||document.body;if(root)new MutationObserver(scheduleSync).observe(root,{subtree:true,childList:true});
    setTimeout(sync,180);setTimeout(sync,800);
  }

  window.DOGSON_NEXT_DAY_CANDIDATES={
    criteria:{qualityMin:QUALITY_MIN,positionMin:POSITION_MIN,chipCoverageMin:CHIP_COVERAGE_MIN,limit:LIMIT},
    rows:()=>currentCandidates(),
    enabled:()=>state.enabled,
    setEnabled:v=>setEnabled(v)
  };

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

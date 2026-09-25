(()=>{
  if(window.__DOGSON_DUAL_DECISION_V1690__) return;
  window.__DOGSON_DUAL_DECISION_V1690__=1;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const firstNum=(r,keys)=>{for(const k of keys){const n=num(r?.[k]);if(n!==null)return n}return null};

  function currentMode(){
    try{if(typeof mode!=='undefined'&&mode)return mode}catch{}
    return $('.tab.active')?.dataset?.mode||'intraday';
  }
  function codeOf(card){return clean(card?.dataset?.code||$('.code',card)?.textContent||'').replace(/[^0-9A-Za-z-]/g,'')}
  function rowFrom(arr,code){return Array.isArray(arr)?arr.find(r=>String(r?.code)===String(code)):null}
  function rowsFor(m){
    try{
      if(m==='daytrade'&&Array.isArray(daytradeRows))return daytradeRows;
      if(m==='close'&&Array.isArray(closeRows))return closeRows;
      if(Array.isArray(intraRows))return intraRows;
    }catch{}
    return [];
  }
  function closeRow(code){try{return rowFrom(closeRows,code)}catch{return null}}
  function currentRow(code,m){return rowFrom(rowsFor(m),code)}

  function marketFor(m){
    try{
      if(m==='close'&&typeof closeMarket!=='undefined')return closeMarket;
      if(typeof market!=='undefined')return market;
      if(typeof intraMarket!=='undefined')return intraMarket;
    }catch{}
    return undefined;
  }

  function entryFor(r,m){
    if(!r)return null;
    try{if(typeof entryDecision==='function')return entryDecision(r,marketFor(m))}catch{}
    return null;
  }
  function stageOf(r){
    if(!r)return'';
    try{if(typeof stageKey==='function')return clean(stageKey(r.category))}catch{}
    return clean(r.category||r.stage||'');
  }
  function qualityOf(r){return clean(r?.quality_label||r?.quality||'')}

  function scoreTone(n){
    if(n===null)return{key:'yellow',label:'待確認'};
    if(n>=78)return{key:'green',label:'強'};
    if(n>=68)return{key:'yellow',label:'可觀察'};
    return{key:'red',label:'偏弱'};
  }

  function swingAxis(code,m,current){
    const base=(m==='intraday'?closeRow(code):current)||current;
    const n=firstNum(base,['swing_score','score','base_score','close_score']);
    let tone=scoreTone(n);
    const st=stageOf(base),q=qualityOf(base);
    if(/失效|轉弱/.test(st))tone={key:'red',label:'結構轉弱'};
    else if(/過熱/.test(st)&&tone.key==='green')tone={key:'yellow',label:'趨勢強但偏熱'};
    else if(/趨勢|持有|剛啟動/.test(st)&&tone.key==='yellow')tone={key:'green',label:'趨勢成立'};
    return{
      title:'波段結構', key:tone.key,
      value:n===null?tone.label:`${Math.round(n)} · ${tone.label}`,
      note:[st,q].filter(Boolean).join('｜')||'看 60 分K、日K、趨勢與波段延續'
    };
  }

  function entryAxis(card,r,m){
    const d=entryFor(r,m)||{};
    let key=clean(d.key||'');
    if(!['green','yellow','red'].includes(key)){
      const chip=$('.entrylight',card);
      key=chip?.classList.contains('green')?'green':chip?.classList.contains('red')?'red':'yellow';
    }
    const st=stageOf(r);
    if(/過熱/.test(st)&&key==='green')key='yellow';
    if(/失效|轉弱/.test(st))key='red';
    const icon=key==='green'?'🟢':key==='red'?'🔴':'🟡';
    const label=clean(d.label||$('.entrylight',card)?.textContent|| (key==='green'?'可試單':key==='red'?'先不進':'等確認'))
      .replace(/^[🟢🟡🔴]+\s*/,'');
    const why=clean(d.headline||d.wait?.[0]||d.block?.[0]||$('.entryheadline',card)?.textContent||'');
    return{title:'現在位置',key,value:`${icon} ${label}`,note:why||'看回踩、追價距離、VWAP 與短線結構'};
  }

  function daytradeExecution(r){
    const n=firstNum(r,['daytrade_score','score','momentum_score']);
    const state=clean(r?.daytrade_state||r?.execution_state||'');
    let key=n!==null?(n>=75?'green':n>=60?'yellow':'red'):'yellow';
    if(/優先|可執行|強/.test(state))key='green';
    if(/偏弱|不做|避開/.test(state))key='red';
    const icon=key==='green'?'🟢':key==='red'?'🔴':'🟡';
    return{
      title:'盤中執行',key,
      value:n===null?`${icon} ${state||'待確認'}`:`${Math.round(n)} · ${state|| (key==='green'?'可執行':key==='red'?'偏弱':'觀察')}`,
      note:'只看今天的 5分K、VWAP、量速與風險'
    };
  }

  function daytradeTiming(card,r){
    const st=clean(r?.daytrade_state||r?.setup||stageOf(r));
    let key='yellow';
    if(/優先|可執行|回踩完成|站回/.test(st))key='green';
    if(/偏弱|過熱|不做|失效/.test(st))key='red';
    const chip=$('.entrylight',card);
    if(chip?.classList.contains('green'))key='green';
    if(chip?.classList.contains('red'))key='red';
    const icon=key==='green'?'🟢':key==='red'?'🔴':'🟡';
    return{
      title:'現在位置',key,value:`${icon} ${key==='green'?'可執行':key==='red'?'不追':'等回踩／確認'}`,
      note:'波段與昨日法人只當背景，不加進當沖分'
    };
  }

  function overall(a,b,m){
    let key='yellow';
    if(a.key==='red'||b.key==='red')key='red';
    else if(a.key==='green'&&b.key==='green')key='green';
    const text=m==='daytrade'
      ?(key==='green'?'可執行':key==='red'?'先不做':'等回踩／確認')
      :(key==='green'?'可試單':key==='red'?'不追':'等回踩／等確認');
    return{key,icon:key==='green'?'🟢':key==='red'?'🔴':'🟡',text};
  }

  function modeCopy(m){
    if(m==='daytrade')return{title:'🎯 當沖雙軸',sub:'今天能不能做 × 現在能不能下手；波段背景不混入當沖分。'};
    if(m==='close')return{title:'🌙 盤後波段雙軸',sub:'波段延續 × 進場位置；好股票不等於明天可以直接追。'};
    return{title:'⚡ 盤中波段雙軸',sub:'波段結構 × 盤中位置；今天急拉不會把普通股票變成波段好股。'};
  }

  function ensureGuide(){
    const controls=$('.controls');if(!controls)return;
    let box=$('#dogsonDualAxisGuide');
    if(!box){
      box=document.createElement('div');box.id='dogsonDualAxisGuide';box.className='dogson-dual-guide';
      controls.after(box);
    }
    const m=currentMode(),c=modeCopy(m);
    const html=`<div class="dogson-dual-guide-title">${esc(c.title)}</div><div class="dogson-dual-guide-sub">${esc(c.sub)}</div><div class="dogson-dual-guide-rule">判斷順序：先看「標的／執行品質」→ 再看「現在位置」→ 兩者都過關才亮綠燈。</div>`;
    if(box.dataset.html!==html){box.innerHTML=html;box.dataset.html=html}
  }

  function renderCard(card){
    const code=codeOf(card),m=currentMode();if(!code)return;
    const r=currentRow(code,m);if(!r)return;
    const a=m==='daytrade'?daytradeExecution(r):swingAxis(code,m,r);
    const b=m==='daytrade'?daytradeTiming(card,r):entryAxis(card,r,m);
    const o=overall(a,b,m),copy=modeCopy(m);
    let box=$('.dogson-dual-decision',card);
    if(!box){
      box=document.createElement('section');box.className='dogson-dual-decision';
      const anchor=$('.dogson-card-brief',card)||$('.dogson-action-strip-v164',card)||$('.top',card);
      anchor?.after(box);
    }
    const html=`
      <div class="dogson-dual-top">
        <div><div class="dogson-dual-kicker">${esc(copy.title.replace(/^[^ ]+\s*/,''))}</div><div class="dogson-dual-final ${o.key}">${o.icon} ${esc(o.text)}</div></div>
        <div class="dogson-dual-eq">兩軸判讀</div>
      </div>
      <div class="dogson-dual-axes">
        <div class="dogson-dual-axis ${a.key}"><div class="dogson-dual-axis-title">① ${esc(a.title)}</div><div class="dogson-dual-axis-value">${esc(a.value)}</div><div class="dogson-dual-axis-note">${esc(a.note)}</div></div>
        <div class="dogson-dual-axis ${b.key}"><div class="dogson-dual-axis-title">② ${esc(b.title)}</div><div class="dogson-dual-axis-value">${esc(b.value)}</div><div class="dogson-dual-axis-note">${esc(b.note)}</div></div>
      </div>
      <div class="dogson-dual-foot">${m==='daytrade'?'當沖：只在今天的執行條件與位置同時成立時出手。':'波段：先確認股票值得抱，再確認現在不是追在不漂亮的位置。'}</div>`;
    if(box.dataset.html!==html){box.innerHTML=html;box.dataset.html=html;box.dataset.tone=o.key}
  }

  function installStyle(){
    if($('#dogsonDualDecisionStyle'))return;
    const s=document.createElement('style');s.id='dogsonDualDecisionStyle';s.textContent=`
      .dogson-dual-guide{margin:10px 0 12px;padding:11px 12px;border:1px solid #d9e1ea;border-radius:14px;background:rgba(255,255,255,.72);box-shadow:0 5px 18px rgba(25,40,60,.05)}
      .dogson-dual-guide-title{font-size:13px;font-weight:900;color:#1d2a39}.dogson-dual-guide-sub{margin-top:4px;font-size:11px;line-height:1.55;color:#536274}.dogson-dual-guide-rule{margin-top:7px;padding-top:7px;border-top:1px dashed #d6dee7;font-size:10px;line-height:1.5;color:#748194}
      .dogson-dual-decision{margin:9px 0 10px;padding:10px;border:1px solid #d8e0e9;border-radius:14px;background:rgba(248,250,252,.92)}
      .dogson-dual-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}.dogson-dual-kicker{font-size:9px;font-weight:850;color:#7b8797}.dogson-dual-final{margin-top:2px;font-size:16px;font-weight:950}.dogson-dual-final.green{color:#b32934}.dogson-dual-final.yellow{color:#a16c05}.dogson-dual-final.red{color:#267744}.dogson-dual-eq{font-size:9px;color:#8591a0;background:#eef2f6;border-radius:999px;padding:5px 7px;white-space:nowrap}
      .dogson-dual-axes{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.dogson-dual-axis{min-width:0;padding:8px;border:1px solid #e0e6ed;border-radius:11px;background:#fff}.dogson-dual-axis.green{border-color:#efc9cd}.dogson-dual-axis.yellow{border-color:#ead9ae}.dogson-dual-axis.red{border-color:#c9dfcf}.dogson-dual-axis-title{font-size:9px;color:#7a8796}.dogson-dual-axis-value{font-size:12px;font-weight:900;margin-top:3px;color:#263443}.dogson-dual-axis-note{font-size:9px;line-height:1.45;color:#7d8998;margin-top:4px}.dogson-dual-foot{font-size:9px;line-height:1.45;color:#7c8897;margin-top:7px}
      html[data-theme="dark"] .dogson-dual-guide,body.dark .dogson-dual-guide,.dark .dogson-dual-guide{background:#121923;border-color:#2a3442}.dark .dogson-dual-guide-title{color:#eef3fa}.dark .dogson-dual-guide-sub,.dark .dogson-dual-guide-rule{color:#9aa7b8;border-color:#303b49}.dark .dogson-dual-decision{background:#111821;border-color:#2a3442}.dark .dogson-dual-axis{background:#0e141c;border-color:#293442}.dark .dogson-dual-axis-value{color:#eef3fb}.dark .dogson-dual-axis-title,.dark .dogson-dual-axis-note,.dark .dogson-dual-foot{color:#93a0b1}.dark .dogson-dual-eq{background:#1d2632;color:#a7b2c1}
      @media(max-width:430px){.dogson-dual-axis-note{font-size:8.5px}.dogson-dual-final{font-size:15px}}
    `;document.head.appendChild(s);
  }

  let pending=false;
  function apply(){
    if(pending)return;pending=true;
    requestAnimationFrame(()=>{pending=false;installStyle();ensureGuide();$$('.card').forEach(renderCard)});
  }
  const obs=new MutationObserver(apply);
  function start(){
    installStyle();apply();
    const list=$('#list')||document.body;obs.observe(list,{childList:true,subtree:true});
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab'))setTimeout(apply,0)});
    window.addEventListener('dogson:freshness',()=>setTimeout(apply,0));
    window.addEventListener('dogson:mode',()=>setTimeout(apply,0));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

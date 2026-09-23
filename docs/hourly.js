(()=>{
  const DATA_URL='./data/hourly.json';
  const LIFE={
    PRE_CROSS:{emoji:'🟡',label:'金叉前夕'},
    EARLY:{emoji:'🟢',label:'初升金叉'},
    STABLE_CONT:{emoji:'🔵',label:'穩定續航'},
    ACCEL_CONT:{emoji:'🚀',label:'加速續航'}
  };
  const DIR={UP:'↗',FLAT:'→',DOWN:'↘'};
  const LIGHT_ORDER={GREEN:0,YELLOW:1,ORANGE:2,RED:3};
  let data={rows:[]};
  let byCode=new Map();
  let selected='ALL';
  let hourlyExpanded=false;

  function n(v,d=1){const x=Number(v);return Number.isFinite(x)?x.toFixed(d):'—'}
  function signed(v,d=1){const x=Number(v);return Number.isFinite(x)?`${x>=0?'+':''}${x.toFixed(d)}%`:'—'}
  function life(r){return LIFE[r?.category60]||{emoji:'⏱️',label:'60K觀察'}}
  function crossText(r){
    if(!r)return'—';
    if(r.category60==='PRE_CROSS')return'金叉前夕';
    const x=Number(r.cross_age);
    return Number.isFinite(x)?`金叉${x}根`:'已金叉';
  }

  function ensureStyles(){
    if(document.getElementById('hourlyStyles'))return;
    const s=document.createElement('style');
    s.id='hourlyStyles';
    s.textContent=`
      .hourlybox{background:linear-gradient(180deg,#151c27,#111720);border:1px solid #2a3140;border-radius:18px;padding:13px;margin:12px 0}
      .hourlytop{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.hourlytitle{font-size:18px;font-weight:900}.hourlysub{font-size:11px;color:#9ba5b6;margin-top:4px;line-height:1.5}.hourlystamp{font-size:10px;color:#9ba5b6;text-align:right;white-space:nowrap}
      .hourlytoggle{border:1px solid #36506f;background:#17304a;color:#cde6ff;border-radius:10px;padding:7px 10px;font-size:11px;font-weight:850;white-space:nowrap}.hourlysummary{font-size:11px;color:#9ba5b6;margin-top:7px}
      .hourlyfilters{display:flex;gap:7px;overflow:auto;padding:10px 0 4px}.hourlyfilter{white-space:nowrap;border:1px solid #2a3140;background:#242b38;color:#c7cfdb;padding:7px 10px;border-radius:999px;font-size:11px;font-weight:800}.hourlyfilter.on{border-color:#4d8ac7;color:#b9ddff;background:#17304a}
      .hourlylist{display:grid;gap:7px;margin-top:8px}.hourlyrow{width:100%;text-align:left;border:1px solid #29313e;background:#0e131a;color:#f4f6fb;border-radius:12px;padding:10px;display:flex;justify-content:space-between;gap:10px}.hourlyrow:active{transform:scale(.995)}.hourlyname{font-size:13px;font-weight:900}.hourlymeta{font-size:10px;color:#9ba5b6;margin-top:4px;line-height:1.5}.hourlyright{text-align:right;min-width:108px}.hourlyscore{font-size:13px;font-weight:900}.hourlylight{font-size:11px;font-weight:850;margin-top:4px}
      .hourlymore{font-size:10px;color:#9ba5b6;margin-top:8px;line-height:1.5}.hourlyempty{color:#9ba5b6;padding:14px 2px;font-size:12px}
      .hourlystrip{margin-top:10px;border:1px solid #31445e;background:#101925;border-radius:12px;padding:9px 10px}.hourlystriptop{display:flex;justify-content:space-between;gap:8px;align-items:center}.hourlylifelabel{font-size:12px;font-weight:900}.hourlyentry{font-size:12px;font-weight:900}.hourlystripmeta{font-size:10px;color:#9ba5b6;margin-top:5px;line-height:1.5}
      @media(max-width:620px){.hourlyrow{padding:9px}.hourlyright{min-width:96px}.hourlymeta{font-size:9.5px}}
    `;
    document.head.appendChild(s);
  }

  function ensureHeaderNote(){
    const sub=document.querySelector('header .sub');
    if(sub&&!sub.dataset.hourly){sub.textContent+='｜60K趨勢＋進場燈號';sub.dataset.hourly='1'}
  }

  function ensureBox(){
    let box=document.getElementById('hourlyRadarBox');
    if(box)return box;
    const controls=document.querySelector('.controls');
    if(!controls)return null;
    box=document.createElement('div');
    box.id='hourlyRadarBox';
    box.className='hourlybox';
    controls.insertAdjacentElement('afterend',box);
    return box;
  }

  function filteredRows(){
    let arr=[...(data.rows||[])];
    if(selected==='GREEN')arr=arr.filter(r=>r.entry_light==='GREEN');
    else if(selected!=='ALL')arr=arr.filter(r=>r.category60===selected);
    arr.sort((a,b)=>{
      const la=LIGHT_ORDER[a.entry_light]??9,lb=LIGHT_ORDER[b.entry_light]??9;
      if(la!==lb)return la-lb;
      return Number(b.combined_score||0)-Number(a.combined_score||0);
    });
    return arr;
  }

  function buttonHTML(key,label){return `<button class="hourlyfilter ${selected===key?'on':''}" data-h60="${key}">${label}</button>`}

  function renderPanel(){
    const box=ensureBox();if(!box)return;
    const isClose=(typeof mode!=='undefined'&&mode==='close');
    box.style.display=isClose?'block':'none';
    if(!isClose)return;
    const rows=filteredRows();
    const counts=data.entry_light_counts||{};
    const updated=data.updated_at?new Date(data.updated_at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
    const body=hourlyExpanded?`
      <div class="hourlyfilters">
        ${buttonHTML('ALL','全部60K')}${buttonHTML('PRE_CROSS','🟡 金叉前夕')}${buttonHTML('EARLY','🟢 初升')}${buttonHTML('STABLE_CONT','🔵 穩定續航')}${buttonHTML('ACCEL_CONT','🚀 加速續航')}${buttonHTML('GREEN',`🟢 位置舒服 ${counts.GREEN??''}`)}
      </div>
      <div class="hourlylist">${rows.length?rows.slice(0,18).map(rowHTML).join(''):'<div class="hourlyempty">目前沒有符合這個60K條件的股票。</div>'}</div>
      <div class="hourlymore">目前共 ${data.rows?.length||0} 檔符合60K生命週期條件；🟢 ${counts.GREEN||0}｜🟡 ${counts.YELLOW||0}｜🟠 ${counts.ORANGE||0}｜🔴 ${counts.RED||0}。點股票會帶到下方完整卡片。</div>`:
      `<div class="hourlysummary">符合 ${data.rows?.length||0} 檔｜🟢位置舒服 ${counts.GREEN||0}｜收合時不占版面，點「展開」再挑60K股票。</div>`;
    box.innerHTML=`
      <div class="hourlytop"><div><div class="hourlytitle">⏱️ 60分K 趨勢雷達</div><div class="hourlysub">四種生命週期＋進場燈號；預設收合，避免手機版被名單擋住。</div></div><div style="display:flex;gap:8px;align-items:flex-start"><div class="hourlystamp">${data.trade_date||''}<br>${updated}</div><button id="hourlyToggle" class="hourlytoggle">${hourlyExpanded?'收合 ▲':'展開 ▼'}</button></div></div>
      ${body}`;
    box.querySelector('#hourlyToggle')?.addEventListener('click',()=>{hourlyExpanded=!hourlyExpanded;renderPanel()});
    box.querySelectorAll('[data-h60]').forEach(b=>b.onclick=()=>{selected=b.dataset.h60;renderPanel()});
    box.querySelectorAll('[data-hourly-code]').forEach(b=>b.onclick=()=>focusStock(b.dataset.hourlyCode));
  }

  function rowHTML(r){
    const l=life(r);
    const dirs=`20T${DIR[r.dir20]||'—'} · 60T${DIR[r.dir60]||'—'} · 240T${DIR[r.dir240]||'—'}`;
    return `<button class="hourlyrow" data-hourly-code="${r.code}"><div><div class="hourlyname">${l.emoji} ${r.name} <span style="color:#9ba5b6;font-weight:600">${r.code}</span></div><div class="hourlymeta">${l.label}｜${dirs}<br>${crossText(r)}｜20/60斜率差 ${n(r.slope_diff,3)}pp｜距20T ${signed(r.price_vs20_60_pct,2)}</div></div><div class="hourlyright"><div class="hourlyscore">60K ${n(r.score60,0)}｜綜合 ${n(r.combined_score,1)}</div><div class="hourlylight">${r.entry_light_emoji||''} ${r.entry_light_label||''}</div></div></button>`;
  }

  function focusStock(code){
    const all=document.querySelector('.filter[data-f="all"]');if(all&&!all.classList.contains('on'))all.click();
    const watch=document.getElementById('watchOnly');if(watch?.classList.contains('on'))watch.click();
    const q=document.getElementById('q');if(q)q.value=String(code);
    try{if(typeof render==='function')render()}catch{}
    setTimeout(()=>{decorateCards();document.getElementById('cards')?.scrollIntoView({behavior:'smooth',block:'start'})},60);
  }

  function codeFromCard(card){
    const t=card.querySelector('.code')?.textContent||'';
    const m=t.match(/\b\d{4}\b/);return m?m[0]:null;
  }

  function decorateCards(){
    const isClose=(typeof mode!=='undefined'&&mode==='close');
    document.querySelectorAll('.hourlystrip').forEach(x=>x.remove());
    if(!isClose)return;
    document.querySelectorAll('.card').forEach(card=>{
      const r=byCode.get(codeFromCard(card));if(!r)return;
      const l=life(r);
      const strip=document.createElement('div');strip.className='hourlystrip';
      strip.title=r.entry_light_reason||'';
      strip.innerHTML=`<div class="hourlystriptop"><div class="hourlylifelabel">${l.emoji} ${l.label}｜60K ${n(r.score60,0)}</div><div class="hourlyentry">${r.entry_light_emoji||''} ${r.entry_light_label||''}</div></div><div class="hourlystripmeta">20T${DIR[r.dir20]||'—'} ${n(r.ma20_60,2)}｜60T${DIR[r.dir60]||'—'} ${n(r.ma60_60,2)}｜240T${DIR[r.dir240]||'—'} ${n(r.ma240_60,2)}<br>${crossText(r)}｜斜率差 ${n(r.slope_diff,3)}pp｜距60K20T ${signed(r.price_vs20_60_pct,2)}${r.entry_light_reason?'｜'+r.entry_light_reason:''}</div>`;
      const top=card.querySelector('.top');if(top)top.insertAdjacentElement('afterend',strip);else card.prepend(strip);
    });
  }

  async function loadHourly(){
    try{
      const r=await fetch(`${DATA_URL}?${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      data=await r.json();
      byCode=new Map((data.rows||[]).map(x=>[String(x.code),x]));
    }catch(e){
      data={rows:[],entry_light_counts:{}};byCode=new Map();
    }
    renderPanel();decorateCards();
  }

  function boot(){
    ensureStyles();ensureHeaderNote();ensureBox();loadHourly();
    document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>{renderPanel();decorateCards()},80)));
    const cards=document.getElementById('cards');if(cards){let t;new MutationObserver(()=>{clearTimeout(t);t=setTimeout(decorateCards,100)}).observe(cards,{childList:true,subtree:true})}
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

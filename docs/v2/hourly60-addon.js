(()=>{
  const LABELS={
    PRE_CROSS:{emoji:'🟡',title:'金叉前夕',tone:'watch'},
    EARLY:{emoji:'🌱',title:'剛啟動',tone:'go'},
    STABLE_CONT:{emoji:'🔵',title:'趨勢中',tone:'trend'},
    ACCEL_CONT:{emoji:'🚀',title:'噴發／加速',tone:'hot'}
  };
  const DIR={UP:'↗',FLAT:'→',DOWN:'↘'};
  const cache=new Map();
  let timer=null;

  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const signed=(v,d=1)=>num(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,d)}%`;
  const shortDate=v=>{const s=String(v||'');return s.length>=10?s.slice(5,10).replace('-','/'):s||'—'};
  const shortTime=v=>{const s=String(v||'');const m=s.match(/T(\d\d:\d\d)/);return m?m[1]:(s.match(/\b(\d\d:\d\d)\b/)||[])[1]||''};

  function ensureStyle(){
    if(document.getElementById('hourly60V2Style'))return;
    const st=document.createElement('style');
    st.id='hourly60V2Style';
    st.textContent=`
      .h60-v2{margin:12px 0;border:1px solid var(--line);border-radius:14px;background:var(--card);overflow:hidden}
      .h60-v2-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 12px;border-bottom:1px solid var(--line)}
      .h60-v2-title{font-size:.82rem;font-weight:900}.h60-v2-date{font-size:.66rem;color:var(--muted);text-align:right}
      .h60-v2-main{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px}
      .h60-v2-life{display:flex;align-items:center;gap:9px;min-width:0}.h60-v2-emoji{font-size:1.45rem}.h60-v2-life b{display:block;font-size:1rem}.h60-v2-life small{display:block;margin-top:3px;color:var(--muted);font-size:.68rem;line-height:1.35}
      .h60-v2-score{white-space:nowrap;text-align:right}.h60-v2-score b{font-size:1.05rem}.h60-v2-score span{display:block;color:var(--muted);font-size:.65rem;margin-top:2px}
      .h60-v2-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;padding:0 12px 12px}.h60-v2-grid>div{padding:8px 9px;border-radius:10px;background:var(--soft)}.h60-v2-grid span{display:block;color:var(--muted);font-size:.66rem}.h60-v2-grid b{display:block;margin-top:3px;font-size:.82rem}.h60-v2-grid small{display:block;margin-top:3px;color:var(--muted);font-size:.64rem;line-height:1.35}
      .h60-v2-note{margin:0 12px 12px;padding:8px 9px;border-radius:10px;background:var(--soft);font-size:.68rem;line-height:1.45;color:var(--muted)}
      .h60-v2.go{border-left:4px solid var(--green)}.h60-v2.hot{border-left:4px solid #d28a21}.h60-v2.trend{border-left:4px solid #4c7fb3}.h60-v2.watch{border-left:4px solid #b59a32}
      @media(max-width:520px){.h60-v2-grid{grid-template-columns:1fr 1fr}.h60-v2-main{align-items:flex-start}}
    `;
    document.head.appendChild(st);
  }

  async function manifest(){
    const r=await fetch(`./data/current_manifest.json?t=${Date.now()}`,{cache:'no-store'});
    if(!r.ok)throw new Error(`manifest ${r.status}`);
    return r.json();
  }

  async function dataset(view){
    const m=await manifest();
    const key=`stock_detail_${view}`;
    const meta=m.datasets?.[key];
    if(!meta?.url)return null;
    const ck=`${m.active_build_id}:${key}`;
    if(cache.has(ck))return cache.get(ck);
    const r=await fetch(meta.url,{cache:'no-store'});
    if(!r.ok)throw new Error(`${key} ${r.status}`);
    const obj=await r.json();
    cache.clear();
    cache.set(ck,obj);
    return obj;
  }

  function activeView(){
    const v=document.querySelector('.tab.active')?.dataset.view||'intraday';
    return ['intraday','close','daytrade'].includes(v)?v:null;
  }

  function currentCode(){
    const t=document.getElementById('detailTitle')?.textContent||'';
    const m=t.match(/\b\d{4}\b/);
    return m?m[0]:null;
  }

  function lifecycle(h){
    if(!h||h.data_status==='UNAVAILABLE')return {emoji:'⚪',title:'60K資料待補',tone:'watch'};
    if(h.category60&&LABELS[h.category60])return LABELS[h.category60];
    return {emoji:'⚪',title:'60K觀察',tone:'watch'};
  }

  function crossText(h){
    if(!h)return'—';
    if(h.category60==='PRE_CROSS')return'20T 接近 60T';
    const x=num(h.cross_age);
    return x==null?'未偵測近期金叉':`20T/60T 金叉 ${fmt(x,0)} 根`;
  }

  function entryText(h){
    if(!h)return'—';
    const emoji=h.entry_light_emoji||'';
    const label=h.entry_light_label||'—';
    return `${emoji} ${label}`.trim();
  }

  function card(h){
    const life=lifecycle(h),dirs=`20T${DIR[h?.dir20]||'—'} · 60T${DIR[h?.dir60]||'—'} · 240T${DIR[h?.dir240]||'—'}`;
    const date=shortDate(h?.trade_date),time=shortTime(h?.updated_at);
    const candidate=h?.is_candidate?'符合60K生命週期候選':'目前不是60K生命週期候選';
    const note=h?.data_status==='UNAVAILABLE'?(h?.exclusion_reason||'60K資料不足'):(h?.exclusion_reason||candidate);
    return `<section class="h60-v2 ${life.tone}" data-hourly60-v2="1">
      <div class="h60-v2-head"><div class="h60-v2-title">60分K技術狀態</div><div class="h60-v2-date">資料日 ${esc(date)}${time?` · ${esc(time)}`:''}</div></div>
      <div class="h60-v2-main"><div class="h60-v2-life"><div class="h60-v2-emoji">${life.emoji}</div><div><b>${esc(life.title)}</b><small>${esc(dirs)}</small></div></div><div class="h60-v2-score"><b>${h?.score60==null?'—':fmt(h.score60,0)}</b><span>60K 結構分</span></div></div>
      <div class="h60-v2-grid">
        <div><span>20T / 60T / 240T</span><b>${fmt(h?.ma20_60,2)} / ${fmt(h?.ma60_60,2)} / ${fmt(h?.ma240_60,2)}</b><small>${esc(dirs)}</small></div>
        <div><span>金叉狀態</span><b>${esc(crossText(h))}</b><small>20/60差 ${signed(h?.gap20_60_pct,2)}</small></div>
        <div><span>距60K 20T</span><b>${signed(h?.price_vs20_60_pct,2)}</b><small>斜率差 ${fmt(h?.slope_diff,3)} pp</small></div>
        <div><span>進場位置</span><b>${esc(entryText(h))}</b><small>${esc(h?.entry_light_reason||'位置燈號與生命週期分開判讀')}</small></div>
      </div>
      <div class="h60-v2-note">${esc(note)}。60K生命週期是技術結構分類，不取代 V2 的 Stage；進場燈號只表示位置／延伸風險，不是買賣指令。</div>
    </section>`;
  }

  function insert(html){
    const body=document.getElementById('detailBody');
    if(!body||body.querySelector('[data-hourly60-v2]'))return;
    const blocks=[...body.querySelectorAll('.detail-block')];
    const target=blocks.find(b=>/技術|籌碼|即時執行證據|即時量價/.test(b.querySelector('h3')?.textContent||''));
    if(target)target.insertAdjacentHTML('beforebegin',html);
    else{
      const eng=body.querySelector('.engineering');
      if(eng)eng.insertAdjacentHTML('beforebegin',html);else body.insertAdjacentHTML('beforeend',html);
    }
  }

  async function render(){
    const body=document.getElementById('detailBody');
    if(!body||/讀取個股詳情/.test(body.textContent||''))return;
    const code=currentCode(),view=activeView();
    if(!code||!view||body.querySelector('[data-hourly60-v2]'))return;
    try{
      const obj=await dataset(view);
      const h=obj?.items?.[code]?.hourly60;
      if(h)insert(card(h));
    }catch(err){
      console.warn('hourly60 v2 addon',err);
    }
  }

  function schedule(){clearTimeout(timer);timer=setTimeout(render,60)}
  function boot(){
    ensureStyle();
    const body=document.getElementById('detailBody'),title=document.getElementById('detailTitle');
    if(body)new MutationObserver(schedule).observe(body,{childList:true,subtree:true,characterData:true});
    if(title)new MutationObserver(schedule).observe(title,{childList:true,subtree:true,characterData:true});
    document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',schedule));
    schedule();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

(()=>{
  'use strict';

  const nativeFetch=window.fetch.bind(window);
  const cache=new Map();
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const shortDate=v=>{
    const s=String(v||'').slice(0,10);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(s))return '—';
    const [,m,d]=s.split('-');
    return `${Number(m)}/${Number(d)}`;
  };
  const checkedStamp=v=>{
    if(!v)return '—';
    const d=new Date(v);
    if(Number.isNaN(d.getTime()))return String(v);
    return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  };
  const isoDate=v=>String(v||'').slice(0,10);
  const sourceDates=e=>[
    ['外資',e?.foreign_date],
    ['投信',e?.trust_date],
    ['借券',e?.sbl_date],
    ['融資',e?.margin_date],
  ];

  async function getShard(build,view,code){
    const key=`${build}:${view}:${code}`;
    if(cache.has(key))return cache.get(key);
    const url=`./data/builds/${encodeURIComponent(build)}/stock-shards/${encodeURIComponent(view)}/${encodeURIComponent(code)}.json?t=${Date.now()}`;
    const r=await nativeFetch(url,{cache:'no-store',credentials:'same-origin'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    const obj=await r.json();
    cache.set(key,obj);
    return obj;
  }

  function sourceSummary(e){
    return sourceDates(e).map(([k,v])=>`${k} ${v?shortDate(v):'—'}`).join(' · ');
  }

  function aggregateDateLabel(e){
    const dates=[...new Set(sourceDates(e).map(([,v])=>isoDate(v)).filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)))].sort();
    if(!dates.length){
      const fallback=e?.chip_date;
      return {label:shortDate(fallback),mixed:false,latest:isoDate(fallback),complete:false};
    }
    if(dates.length===1)return {label:shortDate(dates[0]),mixed:false,latest:dates[0],complete:sourceDates(e).every(([,v])=>!!v)};
    return {label:`${shortDate(dates[0])}–${shortDate(dates[dates.length-1])}`,mixed:true,latest:dates[dates.length-1],complete:false};
  }

  function stateFor(e,baseDate){
    const checked=e?.chip_checked_at||null;
    const health=String(e?.chip_check_health||'').toUpperCase();
    const sources=sourceDates(e);
    const known=sources.filter(([,v])=>!!v).map(([,v])=>isoDate(v));
    const current=known.filter(x=>x===baseDate).length;
    const allFourKnown=known.length===sources.length;

    if(!checked)return ['⚠️ 尚未重新檢查','warn'];
    if(health==='ERROR')return ['❌ 籌碼更新失敗','error'];
    if(allFourKnown&&current===sources.length&&health!=='PARTIAL')return ['✅ 當日籌碼已更新','ok'];
    if(current>0)return ['🟡 當日籌碼部分更新','warn'];
    if(health==='PARTIAL')return ['⚠️ 已檢查，部分來源異常','warn'];
    if(isoDate(checked)&&baseDate&&isoDate(checked)>=baseDate)return ['⏳ 已檢查，當日籌碼尚未發布','wait'];
    return ['⚠️ 尚未重新檢查','warn'];
  }

  function enhance(shard){
    const e=shard?.evidence||{};
    const strip=document.querySelector('#detailBody .isd-fresh-strip');
    if(!strip)return;
    strip.querySelector('.isd-chip-provenance')?.remove();

    const agg=aggregateDateLabel(e);
    const baseDate=isoDate(shard?.as_of)||isoDate(e?.quote_date)||isoDate(shard?.decision?.as_of);
    const sourceStale=!!(agg.latest&&baseDate&&agg.latest!==baseDate);
    const warn=sourceStale||agg.mixed||!agg.complete;
    const firstLine=strip.querySelector('.isd-fresh-line');
    if(firstLine){
      const spans=firstLine.querySelectorAll('span');
      if(spans.length>=3){
        spans[2].classList.toggle('stale',warn);
        spans[2].innerHTML=`籌碼資料日 <b>${esc(agg.label)}</b>${warn?' ⚠️':''}`;
      }
    }

    const [label,tone]=stateFor(e,baseDate);
    const sourceText=sourceSummary(e);
    const box=document.createElement('div');
    box.className='isd-chip-provenance';
    box.style.cssText='margin-top:7px;padding-top:7px;border-top:1px dashed var(--line);font-size:.68rem;line-height:1.55;color:var(--muted)';
    const toneStyle=tone==='error'?'color:var(--red);font-weight:800':tone==='ok'?'color:var(--green);font-weight:800':'font-weight:800';
    box.innerHTML=`<div><span>最後檢查 <b style="color:var(--text)">${esc(checkedStamp(e.chip_checked_at))}</b></span> · <span style="${toneStyle}">${esc(label)}</span></div><div>${esc(sourceText)}</div><div style="margin-top:3px">「資料日」＝來源資料本身的交易日；「最後檢查」＝系統實際去查來源的時間，兩者不互相代替。若各來源日期不同，資料日會顯示日期範圍。</div>`;
    strip.appendChild(box);
  }

  document.addEventListener('radar:detail-rendered',async ev=>{
    try{
      const code=String(ev.detail?.code||'');
      const view=String(ev.detail?.view||'');
      const build=String(ev.detail?.build||'');
      if(!code||!view||!build)return;
      const shard=await getShard(build,view,code);
      const dialog=document.getElementById('detailDialog');
      if(!dialog?.open)return;
      enhance(shard);
    }catch(err){
      console.warn('chip-freshness-provenance',err);
    }
  });

  document.addEventListener('radar:data-reloaded',()=>cache.clear());
})();

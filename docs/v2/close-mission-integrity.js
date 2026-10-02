(()=>{
  'use strict';
  const TH={quality:75,position:65,confidence:80};
  let manifestCache=null,indexCache=null,detailCache=null,buildCache='';
  let countTimer=null,detailTimer=null;

  const $=s=>document.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const pct=(v,d=1)=>n(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,d)}%`;
  const price=v=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:Number(v)<100?2:Number(v)<1000?1:0});
  const activeView=()=>$('.tab.active')?.dataset?.view||'intraday';
  const range=z=>z?`${price(z.low)}–${price(z.high)}`:'—';
  const v2CloseMode=()=>!document.querySelector('[data-h60-mode="hourly60"]')?.classList.contains('active');

  async function json(url){
    const r=await fetch(url,{cache:'no-store'});
    if(!r.ok)throw new Error(`${url} ${r.status}`);
    return r.json();
  }
  async function manifest(force=false){
    if(manifestCache&&!force)return manifestCache;
    const m=await json(`./data/current_manifest.json?t=${Date.now()}`);
    const build=String(m.active_build_id||'');
    if(build!==buildCache){buildCache=build;indexCache=null;detailCache=null}
    manifestCache=m;
    return m;
  }
  async function dataset(key){
    const m=await manifest();
    const meta=m.datasets?.[key];
    if(!meta?.url)return null;
    return json(meta.url);
  }
  async function closeIndex(){
    if(indexCache)return indexCache;
    indexCache=await dataset('decision_close_index')||[];
    return indexCache;
  }
  async function closeDetail(){
    if(detailCache)return detailCache;
    detailCache=await dataset('decision_close_detail')||{items:{}};
    return detailCache;
  }

  function elite(d){
    const s=d?.scores||{};
    return d?.opportunity_bucket==='NEXT_DAY_READY'
      && n(s.swing_quality_score)!=null&&n(s.swing_quality_score)>=TH.quality
      && n(s.entry_position_score)!=null&&n(s.entry_position_score)>=TH.position
      && n(d?.data_confidence)!=null&&n(d.data_confidence)>=TH.confidence
      && !['WEAKENING','FAILED'].includes(d?.lifecycle_stage)
      && !['DO_NOT_CHASE','REDUCE_WATCH','EXIT_PRIORITY','DATA_STALE'].includes(d?.action_state);
  }

  async function repairCounts(){
    if(activeView()!=='close')return;
    const host=$('#radarSummary');
    if(!host)return;
    try{
      const [idx,det]=await Promise.all([closeIndex(),closeDetail()]);
      const details=Object.values(det?.items||{});
      const counts={
        NEXT_DAY_READY:details.filter(elite).length,
        LAUNCH:idx.filter(x=>x?.lifecycle_stage==='LAUNCH').length,
        PULLBACK:idx.filter(x=>['PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(x?.lifecycle_stage)).length,
        RISK:idx.filter(x=>x?.opportunity_bucket==='RISK').length
      };
      for(const [key,value] of Object.entries(counts)){
        const tile=host.querySelector(`[data-quick-filter="${key}"]`);
        const strong=tile?.querySelector('strong');
        if(strong)strong.textContent=Number(value).toLocaleString('zh-TW');
      }
      const next=host.querySelector('[data-quick-filter="NEXT_DAY_READY"] small');
      if(next)next.textContent=`品質≥${TH.quality}・位置≥${TH.position}・信心≥${TH.confidence}・不設檔數上限`;
      // 60K mode writes its own count label. Restore the V2 label as soon as
      // the user switches back so the two missions never leak into each other.
      if(v2CloseMode()&&$('#countText'))$('#countText').textContent=`V2盤後 · ${idx.length.toLocaleString('zh-TW')} 檔`;
    }catch(err){console.warn('close count integrity repair',err)}
  }

  function unique(xs){return [...new Set((xs||[]).filter(Boolean).map(String))]}
  function deriveBlockers(d,e,zones){
    const out=[...(d.blockers||[])];
    const rs=zones.filter(z=>z.side==='RESISTANCE').sort((a,b)=>(n(a.distance_pct)??999)-(n(b.distance_pct)??999));
    const r=rs[0];
    if(!out.length&&r&&n(r.distance_pct)!=null&&n(r.distance_pct)<=3){
      out.push(`距第一壓力 ${range(r)} 約 ${pct(r.distance_pct)}，先確認能否有效站上。`);
    }
    const pos=n(d?.scores?.entry_position_score);
    if(pos!=null&&pos<65)out.push(`進場位置分 ${fmt(pos,0)}/100，尚未達舒適區。`);
    const chip=n(e?.chip_score);
    if(chip!=null&&chip<12)out.push(`籌碼分 ${fmt(chip,0)}/25，籌碼尚未同步轉強。`);
    return unique(out).slice(0,4);
  }
  function deriveUpgrades(d,e,zones){
    const out=[...(d.upgrade_conditions||[])];
    const rs=zones.filter(z=>z.side==='RESISTANCE').sort((a,b)=>(n(a.distance_pct)??999)-(n(b.distance_pct)??999));
    const r=rs[0];
    if(!out.length&&r){
      out.push(`第一壓力 ${range(r)}：${r.validation_condition||'有效站上壓力上緣且量價同步，回測不破才算突破確認。'}`);
    }
    if(d.lifecycle_stage==='LAUNCH'){
      out.push('突破後維持量價結構、不要快速跌回突破區，才有機會由「剛啟動」升級為趨勢。');
    }
    if(n(e?.chip_score)!=null&&n(e.chip_score)<12){
      out.push('籌碼改善條件：外資賣壓收斂／轉買，且借券不再擴增。');
    }
    return unique(out).slice(0,4);
  }
  function deriveRisks(d,e,zones){
    const out=[...(d.risk_flags||[]),...(e?.stage_risks||[]),...(e?.overheat_reasons||[])];
    const ss=zones.filter(z=>z.side==='SUPPORT').sort((a,b)=>String(a.rank||'').localeCompare(String(b.rank||'')));
    const s=ss[0];
    if(!out.length&&s){
      out.push(`第一支撐 ${range(s)}：${s.invalidation_condition||'連續兩根對應週期K收在支撐下方，或跌破後反抽站不回且量價轉弱，才視為結構失效。'}`);
    }
    const dist=n(e?.dist20);
    if(dist!=null&&dist>=8)out.push(`距20MA ${pct(dist)}，短線乖離偏大，避免追高。`);
    if(String(e?.margin_status||'').includes('熱')||(n(e?.margin_3d_pct)!=null&&n(e.margin_3d_pct)>=5)){
      out.push(`融資3日 ${pct(e?.margin_3d_pct)}，籌碼偏熱；若價格同步轉弱需提高警戒。`);
    }
    return unique(out).slice(0,4);
  }

  function setSection(titlePrefix,items){
    const body=$('#detailBody');if(!body)return false;
    const h=[...body.querySelectorAll('.isd-section h3')].find(x=>(x.textContent||'').trim().startsWith(titlePrefix));
    if(!h)return false;
    const sec=h.parentElement;
    const title=h.textContent;
    sec.innerHTML=`<h3>${esc(title)}</h3><div class="isd-tags">${items.map(x=>`<span>${esc(x)}</span>`).join('')}</div>`;
    return true;
  }

  async function repairDetail(){
    if(activeView()!=='close')return;
    const body=$('#detailBody'),title=$('#detailTitle');
    if(!body||!title||!/\b\d{4}\b/.test(title.textContent||''))return;
    if(!body.querySelector('.isd-section'))return;
    const code=(title.textContent.match(/\b\d{4}\b/)||[])[0];
    if(!code)return;
    try{
      const m=await manifest();
      const shard=await json(`./data/builds/${encodeURIComponent(m.active_build_id)}/stock-shards/close/${code}.json?t=${Date.now()}`);
      if(shard?.build_id!==m.active_build_id)return;
      const d=shard.decision||{},e=shard.evidence||{},zones=Array.isArray(shard.zones)?shard.zones:[];
      const blockers=deriveBlockers(d,e,zones),upgrades=deriveUpgrades(d,e,zones),risks=deriveRisks(d,e,zones);
      if(blockers.length)setSection('現在卡在哪裡',blockers);
      if(upgrades.length)setSection('明日升級條件',upgrades);
      if(risks.length)setSection('失效',risks);
    }catch(err){console.warn('close detail semantics repair',err)}
  }

  function scheduleCounts(ms=120){clearTimeout(countTimer);countTimer=setTimeout(repairCounts,ms)}
  function scheduleDetail(ms=120){clearTimeout(detailTimer);detailTimer=setTimeout(repairDetail,ms)}

  document.addEventListener('radar:view-rendered',()=>{scheduleCounts(120);scheduleCounts(900)});
  document.addEventListener('radar:data-reloaded',async()=>{manifestCache=null;indexCache=null;detailCache=null;await manifest(true).catch(()=>null);scheduleCounts(180);scheduleCounts(1000)});
  document.addEventListener('radar:open-stock',()=>{scheduleDetail(180);scheduleDetail(700)});
  document.addEventListener('click',e=>{
    if(e.target?.closest?.('.tab,[data-quick-filter],[data-quick-filter-clear],[data-h60-mode]')){scheduleCounts(220);scheduleCounts(950)}
    if(e.target?.closest?.('.card[data-code],.h60-screen-card[data-code]')){scheduleDetail(220);scheduleDetail(850)}
  });
  const body=$('#detailBody');if(body)new MutationObserver(()=>scheduleDetail(120)).observe(body,{childList:true,subtree:true});
  setTimeout(()=>{scheduleCounts(0);scheduleDetail(0)},500);
})();
(()=>{
  'use strict';

  const nativeFetch=window.fetch.bind(window);
  let seq=0;
  let activeCloseMode='swing';
  const cache=new Map();
  const isIgnition=view=>view==='close'&&activeCloseMode==='ignition';

  const VIEW={intraday:'盤中波段',close:'盤後波段',daytrade:'當沖'};
  const STAGE={OBSERVE:'觀察',SETUP:'蓄勢待發',LAUNCH:'剛啟動',TREND:'趨勢持有',PULLBACK_TEST:'回踩觀察',PULLBACK_CONFIRMED:'回踩承接',WEAKENING:'轉弱警戒',FAILED:'結構失效'};
  const ACTION={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'};
  const FRESH={LIVE:'即時',FRESH:'盤後定格',FROZEN:'收盤定格',STALE:'過期',UNKNOWN:'未知'};
  const MISSING={swing_quality_score:'波段品質',entry_position_score:'進場位置',intraday_momentum_score:'盤中動能',daytrade_score:'當沖分'};

  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const pct=(v,d=1)=>num(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,d)}%`;
  const price=v=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:Number(v)<100?2:Number(v)<1000?1:0});
  const moneyMn=v=>num(v)==null?'—':`${fmt(Number(v)/1000000,1)} 百萬`;
  const pad=n=>String(n).padStart(2,'0');
  const md=v=>{const d=v?new Date(v):null;return d&&!Number.isNaN(d.getTime())?`${d.getMonth()+1}/${d.getDate()}`:'—'};
  const hm=v=>{const d=v?new Date(v):null;return d&&!Number.isNaN(d.getTime())?`${pad(d.getHours())}:${pad(d.getMinutes())}`:'—'};
  const localStamp=(date,time)=>date&&time?new Date(`${date}T${time}+08:00`):null;

  function injectStyle(){
    if(document.getElementById('inukoDirectStockDetailStyleV2'))return;
    const s=document.createElement('style');
    s.id='inukoDirectStockDetailStyleV2';
    s.textContent=`
      .isd-loading{padding:18px 4px}.isd-loading b{font-size:1rem}.isd-loading p{color:var(--muted);line-height:1.5}
      .isd-context{font-size:.72rem;color:var(--muted);margin:0 0 9px}.isd-hero{display:flex;justify-content:space-between;gap:12px;padding:14px;border-radius:16px;background:var(--soft);margin-bottom:12px}.isd-hero h2{margin:7px 0 4px;font-size:1.35rem}.isd-hero p{margin:0;color:var(--muted);line-height:1.45;font-size:.78rem}.isd-light{align-self:center;padding:8px 12px;border-radius:999px;background:#e7f3ed;font-weight:800;white-space:nowrap}.isd-light.risk{background:#f7e6e2}.isd-badge{display:inline-block;padding:4px 8px;border-radius:999px;background:var(--card);font-size:.72rem;font-weight:800}
      .isd-score{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 9px}.isd-score>div{border:1px solid var(--line);border-radius:12px;padding:10px 8px;text-align:center}.isd-score span{display:block;color:var(--muted);font-size:.7rem}.isd-score b{display:block;margin-top:4px;font-size:1.1rem}
      .isd-fresh-strip{padding:9px 11px;border-radius:11px;background:color-mix(in srgb,var(--green) 7%,var(--soft));margin:0 0 14px}.isd-fresh-line{display:flex;gap:7px 12px;flex-wrap:wrap;font-size:.72rem}.isd-fresh-line b{font-weight:850}.isd-fresh-line .stale{color:var(--red)}.isd-fresh-age{margin-top:4px;color:var(--muted);font-size:.68rem}
      .isd-section{margin:14px 0}.isd-section h3{margin:0 0 8px;font-size:.92rem}.isd-tags{display:flex;flex-wrap:wrap;gap:7px}.isd-tags span{padding:6px 9px;border-radius:999px;background:var(--soft);font-size:.76rem}.isd-muted{color:var(--muted);font-size:.76rem;line-height:1.5}
      .isd-zones{display:grid;gap:9px}.isd-zone{border:1px solid var(--line);border-radius:13px;padding:11px 12px}.isd-zone.support{border-left:4px solid var(--green)}.isd-zone.resistance{border-left:4px solid var(--red)}.isd-zone-head{display:flex;justify-content:space-between;gap:10px;font-size:.76rem}.isd-zone-price{font-size:1.25rem;font-weight:900;margin:5px 0}.isd-zone small{display:block;color:var(--muted);line-height:1.45}
      .isd-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.isd-grid>div{background:var(--soft);border-radius:10px;padding:9px}.isd-grid span{display:block;color:var(--muted);font-size:.68rem}.isd-grid b{display:block;margin-top:3px;font-size:.86rem;line-height:1.35}.isd-grid small{display:block;margin-top:3px;color:var(--muted);font-size:.64rem;line-height:1.35}
      .isd-explain{border:1px solid var(--line);border-radius:12px;background:var(--soft);margin:14px 0}.isd-explain summary{padding:10px 12px;font-weight:800;cursor:pointer}.isd-exp{padding:0 11px 11px}.isd-exp-card{padding:9px 0;border-top:1px dashed var(--line)}.isd-exp-head{display:flex;justify-content:space-between;gap:12px;font-size:.8rem}.isd-exp-item{display:grid;grid-template-columns:42px 1fr;gap:4px 7px;margin-top:5px;font-size:.74rem}.isd-exp-detail{grid-column:2;color:var(--muted);font-size:.68rem;line-height:1.4}
      .isd-quality{border:1px solid var(--line);border-radius:12px;padding:11px 12px}.isd-quality-note{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line);color:var(--muted);font-size:.7rem;line-height:1.5}.isd-quality-note strong{color:inherit}.isd-diagnostic{margin-top:9px;color:var(--muted);font-size:.68rem}.isd-diagnostic summary{cursor:pointer}.isd-diagnostic div{padding-top:6px;line-height:1.55;word-break:break-all}.isd-error{padding:14px;border:1px solid #d8b5ad;border-radius:12px;background:#fff3ef;line-height:1.55}
      @media(max-width:520px){.isd-hero{align-items:flex-start}.isd-score{grid-template-columns:repeat(3,1fr)}.isd-grid{grid-template-columns:repeat(2,1fr)}}`;
    document.head.appendChild(s);
  }

  async function json(url,ms=8000){
    const controller=typeof AbortController!=='undefined'?new AbortController():null;
    const timer=controller?setTimeout(()=>controller.abort(),ms):0;
    try{
      const r=await nativeFetch(url,{cache:'no-store',credentials:'same-origin',...(controller?{signal:controller.signal}:{})});
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      return await r.json();
    }finally{if(timer)clearTimeout(timer)}
  }

  function ui(code){
    const dialog=document.getElementById('detailDialog'),title=document.getElementById('detailTitle'),body=document.getElementById('detailBody');
    if(!dialog||!title||!body)return null;
    title.textContent=`${code} 個股詳情`;
    body.innerHTML='<div class="isd-loading"><b>讀取個股詳情…</b><p>正在載入這一檔自己的完整資料。</p></div>';
    if(!dialog.open){try{dialog.showModal()}catch{dialog.setAttribute('open','')}}
    return{dialog,title,body};
  }

  function range(z){
    if(!z)return'—';
    const lo=num(z.low),hi=num(z.high);
    if(lo==null&&hi==null)return'—';
    if(lo===hi)return price(lo);
    return `${price(lo)}–${price(hi)}`;
  }
  function tags(xs,empty='目前沒有額外條件。'){
    const a=[...new Set((xs||[]).filter(Boolean).map(String))];
    return a.length?`<div class="isd-tags">${a.map(x=>`<span>${esc(x)}</span>`).join('')}</div>`:`<div class="isd-muted">${esc(empty)}</div>`;
  }
  function scoreTile(label,value){return `<div><span>${esc(label)}</span><b>${esc(value)}</b></div>`}
  function metric(label,value,sub=''){return `<div><span>${esc(label)}</span><b>${esc(value)}</b>${sub?`<small>${esc(sub)}</small>`:''}</div>`}

  function mainScore(view,d){
    const s=d.scores||{};
    if(view==='intraday')return ['盤中動能',fmt(s.intraday_momentum_score)];
    if(view==='daytrade')return ['當沖分',fmt(s.daytrade_score)];
    return isIgnition(view)?['點火分數',fmt(s.ignition_score)]:['波段品質',fmt(s.swing_quality_score)];
  }
  function light(view,d){
    if(isIgnition(view)){
      if(d.ignition_stage==='末端過熱／不追'||d.ignition_execution_state==='NO_CHASE')return['過熱不追','risk'];
      if(d.ignition_execution_ready===true)return['可試單',''];
      return[d.ignition_stage||'先等待',''];
    }
    const risk=['EXIT_PRIORITY','REDUCE_WATCH'].includes(d.action_state)||['FAILED','WEAKENING'].includes(d.lifecycle_stage);
    if(risk)return['風險優先','risk'];
    if(view==='daytrade'&&!(d.session_phase==='LIVE'&&d.freshness==='LIVE'))return['不可執行',''];
    if(view==='intraday'&&!(d.session_phase==='LIVE'&&d.freshness==='LIVE'))return['收盤定格',''];
    if(d.actionable)return['可執行',''];
    return['先等待',''];
  }
  function heroText(view,d){
    if(isIgnition(view))return d.ignition_summary||'點火強度只代表加速訊號；是否買進仍需看進場位置及隔日即時確認。';
    if(['EXIT_PRIORITY','REDUCE_WATCH'].includes(d.action_state)||['FAILED','WEAKENING'].includes(d.lifecycle_stage))return'結構轉弱，先處理風險。';
    if(view==='close')return d.actionable?'盤後條件已同步，明天仍要用即時量價確認。':'目前先列觀察，條件成立前不用追。';
    if(view==='daytrade'&&!(d.session_phase==='LIVE'&&d.freshness==='LIVE'))return'當沖只在即時資料合格時有效；這份資料只供回看。';
    if(view==='intraday'&&!(d.session_phase==='LIVE'&&d.freshness==='LIVE'))return'這是盤中最後快照，只供回看；下個交易日重新確認。';
    return d.actionable?'目前條件已同步，但仍要守住支撐與追價限制。':'目前還差觸發條件，先看不要急著進。';
  }

  function zoneHtml(z){
    const side=z.side==='SUPPORT'?'support':'resistance';
    const label=z.side==='SUPPORT'?'支撐':'壓力';
    return `<div class="isd-zone ${side}"><div class="isd-zone-head"><b>${esc(z.label||label)}</b><span>${esc(z.rank||'')}</span></div><div class="isd-zone-price">${range(z)}</div><small>距離 ${pct(z.distance_pct)}｜強度 ${fmt(z.strength,1)}｜${esc((z.evidence||[]).join('＋')||'結構區')}</small></div>`;
  }

  function intradayEvidence(e){
    const m5=e?.multi_timeframe?.['5m'],m60=e?.multi_timeframe?.['60m'],daily=e?.multi_timeframe?.daily,rel=e?.relative_multiframe;
    return `<div class="isd-grid">
      ${metric('現價',price(e.close),`當日 ${pct(e.day_change)}`)}
      ${metric('VWAP',price(e.vwap),`距 VWAP ${pct(e.vwap_dist)}`)}
      ${metric('15分漲跌',pct(e.ret15),rel?.label||'短線相對強弱')}
      ${metric('量速',num(e.pace)==null?'—':`${fmt(e.pace,1)}x`,`目前成交額 ${moneyMn(e.current_turnover)}`)}
      ${metric('20日均成交額',num(e.avg_turnover20_mn)==null?'—':`${fmt(e.avg_turnover20_mn,1)} 百萬`,e.liquidity_level?`流動性：${e.liquidity_level}`:'')}
      ${metric('買一 / 賣一',`${price(e.quote_bid1)} / ${price(e.quote_ask1)}`,e.quote_source||'盤中報價')}
      ${metric('5分結構',m5?.label||'—',m5?.above_vwap?'站上 VWAP':'')}
      ${metric('60分結構',m60?.label||'—',m60?.source_trade_date?`歷史底稿 ${m60.source_trade_date}`:'')}
      ${metric('日K結構',daily?.label||'—',daily?.source_date?`底稿 ${daily.source_date}`:'')}
      ${metric('籌碼背景',e.chip_background||'—',num(e.chip_score)==null?'':`籌碼分 ${fmt(e.chip_score,0)}`)}
      ${metric('族群狀態',e.sector_score_label||e.industry_name||'—',num(e.sector_score)==null?'':`族群分 ${fmt(e.sector_score,1)}`)}
      ${metric('結構信心',e.structure_confidence||'—',e.stage_reason||'')}
    </div>`;
  }

  function closeEvidence(e){
    return `<div class="isd-grid">${metric('收盤',price(e.close))}${metric('漲跌',pct(e.day_change))}${metric('量比',num(e.vol_x)==null?'—':`${fmt(e.vol_x,1)}x`)}${metric('距20MA',pct(e.dist20))}${metric('RSI',fmt(e.rsi,1))}${metric('MACD柱',fmt(e.macd_h,2))}${metric('外資今日',num(e.foreign_net_latest)==null?'—':`${fmt(e.foreign_net_latest/1000,1)}張`)}${metric('投信今日',num(e.trust_net_latest)==null?'—':`${fmt(e.trust_net_latest/1000,1)}張`)}${metric('借券3日',pct(e.sbl_3change_pct))}${metric('融資3日',pct(e.margin_3d_pct))}${metric('族群 2.0',num(e.sector_score_v2)==null?'—':`${fmt(e.sector_score_v2,1)}/15`,e.sector_summary_v2||'')}${metric('流動性 2.0',num(e.liquidity_score_v2)==null?'—':`${fmt(e.liquidity_score_v2,1)}/10`,e.liquidity_summary_v2||'')}</div>`;
  }

  function evidenceHtml(e,view){
    if(!e)return'<div class="isd-muted">這份單股資料沒有可用證據。</div>';
    if(view==='close')return closeEvidence(e);
    if(view==='intraday')return intradayEvidence(e);
    return intradayEvidence(e);
  }

  function v2BreakdownCard(label,total,max,parts,order,kind){
    if(!parts||typeof parts!=='object')return'';
    const rows=order.map(k=>{
      const p=parts[k]; if(!p)return'';
      const points=kind==='chip'?num(p.points):num(p.score);
      const denom=kind==='chip'?num(p.weight):num(p.max);
      const sub=kind==='chip'&&num(p.score)!=null?` · 子分 ${fmt(p.score,0)}/100`:'';
      return `<div class="isd-exp-item"><b>${points==null?'—':`${fmt(points,1)}/${fmt(denom,0)}`}</b><span>${esc(p.label||k)}</span>${p.detail||sub?`<span class="isd-exp-detail">${esc((p.detail||'')+sub)}</span>`:''}</div>`;
    }).join('');
    return `<div class="isd-exp-card"><div class="isd-exp-head"><b>${esc(label)}</b><strong>${fmt(total,1)}/${fmt(max,0)}</strong></div>${rows||'<div class="isd-muted">2.0 分項證據待補。</div>'}</div>`;
  }

  function explainHtml(d,e,view){
    if(isIgnition(view)){
      const parts=e?.ignition_components_v2||null;
      const raw=num(d.ignition_raw_score)??num(e?.ignition_raw_score_v2);
      const cap=num(d.ignition_gate_cap)??num(e?.ignition_gate_cap_v2)??100;
      const finalScore=num(d.scores?.ignition_score)??num(e?.ignition_score_v2);
      const confidence=num(d.ignition_confidence)??num(e?.ignition_confidence_v2);
      const dist=num(d.ignition_breakout_distance_atr)??num(e?.ignition_breakout_distance_atr_v2);
      const flags=(d.ignition_gate_flags||e?.ignition_gate_flags_v2||[]).filter(Boolean);
      const order=['structure','volume_acceleration','sector_resonance','relative_acceleration','chip_acceleration','tradability_risk'];
      const scores=parts?v2BreakdownCard('🔥 點火 2.0 六項分數',raw,100,parts,order,'technical'):'<div class="isd-muted">點火六項證據待盤後重建補齊。</div>';
      const gate=flags.length?flags.join('、'):'未觸發封頂';
      return `<details class="isd-explain" open><summary>🔥 點火 2.0｜為什麼是這個分數</summary><div class="isd-exp"><div class="isd-muted"><b>Final ${fmt(finalScore,1)}/100 = Raw ${fmt(raw,1)}/100 → Gate ${fmt(cap,1)}/100</b><br>階段：${esc(d.ignition_stage||'—')}｜點火信心 ${fmt(confidence,0)}%｜距突破點 ${dist==null?'—':fmt(dist,2)+' ATR'}<br>Gate：${esc(gate)}<br>進場位置 ${fmt(d.scores?.entry_position_score,1)}/100｜${esc(d.ignition_execution_note||'仍須隔日確認量價')}</div>${scores}<div class="isd-muted">點火100＝起漲／突破25＋量能加速20＋族群共振15＋相對強度加速15＋籌碼加速15＋可交易性／風險10。點火高分不代表現在適合追價。</div></div></details>`;
    }
    if(view==='intraday'&&d.components?.intraday?.items?.length){
      const details={
        price_structure:e?`VWAP ${price(e.vwap)}｜距 VWAP ${pct(e.vwap_dist)}｜5分 ${e.multi_timeframe?.['5m']?.label||'—'}`:'',
        flow_volume:e?`量速 ${num(e.pace)==null?'—':`${fmt(e.pace,1)}x`}｜15分漲跌 ${pct(e.ret15)}`:'',
        relative_strength:e?.relative_multiframe?.label||'',
        sector:e?.sector_score_label?`${e.sector_score_label}｜族群分 ${fmt(e.sector_score,1)}`:'',
        liquidity_risk:e?`20日均成交額 ${num(e.avg_turnover20_mn)==null?'—':`${fmt(e.avg_turnover20_mn,1)} 百萬`}｜${e.liquidity_level||'流動性待補'}`:''
      };
      return `<details class="isd-explain"><summary>評分依據｜為什麼是這個分數</summary><div class="isd-exp"><div class="isd-muted">盤中動能由 Engine 分項加總；前端只翻成可讀證據，不重新配分。</div>${d.components.intraday.items.map(i=>`<div class="isd-exp-card"><div class="isd-exp-head"><b>${esc(i.label||i.key||'分項')}</b><strong>${fmt(i.contribution)}/${fmt(i.contribution_max,0)}</strong></div>${details[i.key]?`<div class="isd-exp-detail" style="grid-column:auto;margin-top:5px">${esc(details[i.key])}</div>`:''}</div>`).join('')}<div class="isd-muted">分數代表條件同步程度，不代表上漲機率。</div></div></details>`;
    }

    const x=d.score_explanations||null;
    if(view==='close'&&e){
      const hasTech2=e.technical_model_version==='inuko-tech-v2.0'&&e.technical_components_v2;
      const hasChip2=e.chip_model_version==='inuko-chip-v2.0'&&e.chip_components_v2;
      const hasSector2=e.sector_model_version==='inuko-sector-v2.0'&&e.sector_components_v2;
      const hasLiquidity2=e.liquidity_model_version==='inuko-liquidity-v2.0'&&e.liquidity_components_v2;
      if(hasTech2||hasChip2||hasSector2||hasLiquidity2){
        const tech=hasTech2?v2BreakdownCard('技術 2.0',e.technical_score_v2,50,e.technical_components_v2,['trend','breakout','volume_price','momentum','relative','risk_quality'],'technical'):'';
        const chip=hasChip2?v2BreakdownCard('籌碼 2.0',e.chip_score_v2,25,e.chip_components_v2,['foreign','trust','sbl','margin','consensus','price_chip','sector_inst'],'chip'):'';
        const sector=hasSector2?v2BreakdownCard(`族群 2.0 · ${e.sector_verdict_v2||''}`,e.sector_score_v2,15,e.sector_components_v2,['breadth','leaders','persistence','capital_resonance','structure','taxonomy'],'technical'):'';
        const liquidity=hasLiquidity2?v2BreakdownCard(`流動性 2.0 · ${e.liquidity_verdict_v2||''}`,e.liquidity_score_v2,10,e.liquidity_components_v2,['avg_turnover','stability','price_impact','continuity','crowding'],'technical'):'';
        const fallbackKeys=[];
        if(!hasSector2)fallbackKeys.push('sector');
        if(!hasLiquidity2)fallbackKeys.push('liquidity');
        fallbackKeys.push('entry_position');
        const rest=x?fallbackKeys.map(k=>{
          const p=x[k]; if(!p)return'';
          return `<div class="isd-exp-card"><div class="isd-exp-head"><b>${esc({sector:'族群',liquidity:'流動性',entry_position:'進場位置'}[k]||k)}</b><strong>${fmt(p.score)}/${fmt(p.max,0)}</strong></div>${(p.items||[]).map(i=>`<div class="isd-exp-item"><b>${num(i.points)>0?'+':''}${fmt(i.points)}</b><span>${esc(i.label||'')}</span>${i.detail?`<span class="isd-exp-detail">${esc(i.detail)}</span>`:''}</div>`).join('')}</div>`;
        }).join(''):'';
        return `<details class="isd-explain"><summary>評分依據｜為什麼是這個分數</summary><div class="isd-exp"><div class="isd-muted">波段品質＝技術50＋籌碼25＋族群15＋流動性10；進場位置另計100。技術6分項、籌碼7分項、族群6分項、流動性5分項各自計分，不重複灌分。</div>${tech}${chip}${sector}${liquidity}${rest}<div class="isd-muted">族群只評估整體共振；個股相對族群強弱留在技術2.0。法人族群共振留在籌碼2.0。流動性採飽和式評分，不因單日爆量或超大型成交額無限加分。</div></div></details>`;
      }
    }

    if(x){
      const parts=['technical','chip','sector','liquidity','entry_position'].map(k=>{
        const p=x[k]; if(!p)return'';
        return `<div class="isd-exp-card"><div class="isd-exp-head"><b>${esc({technical:'技術',chip:'籌碼',sector:'族群',liquidity:'流動性',entry_position:'進場位置'}[k]||k)}</b><strong>${fmt(p.score)}/${fmt(p.max,0)}</strong></div>${(p.items||[]).map(i=>`<div class="isd-exp-item"><b>${num(i.points)>0?'+':''}${fmt(i.points)}</b><span>${esc(i.label||'')}</span>${i.detail?`<span class="isd-exp-detail">${esc(i.detail)}</span>`:''}</div>`).join('')}</div>`;
      }).join('');
      return `<details class="isd-explain"><summary>評分依據｜為什麼是這個分數</summary><div class="isd-exp"><div class="isd-muted">${esc(x.formula||'分數代表條件同步程度，不代表上漲機率。')}</div>${parts}</div></details>`;
    }
    return'';
  }

  function freshnessHtml(shard,d,e,m){
    const quoteTime=e?.quote_snapshot_time||hm(m?.datasets?.index_quote?.as_of);
    const structureTime=hm(shard.known_at||d.known_at||m?.generated_at);
    const chipAsOf=e?.chip_date||e?.foreign_date||e?.trust_date||e?.sbl_date||e?.margin_date||null;
    const chipDate=md(chipAsOf);
    const baseDate=m?.trade_date||e?.quote_date||'';
    const chipSourceDate=chipAsOf?String(chipAsOf).slice(0,10):'';
    const baseSourceDate=baseDate?String(baseDate).slice(0,10):'';
    const chipStale=!!(chipSourceDate&&baseSourceDate&&chipSourceDate!==baseSourceDate);
    const qd=localStamp(e?.quote_date,quoteTime);
    const age=qd&&!Number.isNaN(qd.getTime())?Math.max(0,Math.floor((Date.now()-qd.getTime())/60000)):null;
    return `<div class="isd-fresh-strip"><div class="isd-fresh-line"><span>報價 <b>${esc(quoteTime||'—')}</b></span><span>結構 <b>${esc(structureTime||'—')}</b></span><span class="${chipStale?'stale':''}">籌碼 <b>${esc(chipDate)}</b>${chipStale?' ⚠️':''}</span></div><div class="isd-fresh-age">${age==null?'更新時間待確認':age<=0?'剛剛更新':`${age} 分鐘前更新`}；三種資料各看自己的來源時間，籌碼日期不再用 Build／context 時間代替。</div></div>`;
  }

  function qualityHtml(shard,d,m){
    const cov=num(d.component_coverage),conf=num(d.data_confidence),missing=(d.missing_fields||[]).map(x=>MISSING[x]||x);
    const missText=missing.length?`目前未覆蓋：${missing.join('、')}。`:'目前主要證據已覆蓋。';
    return `<div class="isd-quality"><b>資料品質</b><div class="isd-grid" style="margin-top:8px">${metric('Freshness',FRESH[d.freshness]||d.freshness||'—')}${metric('資料信心',conf==null?'—':`${fmt(conf,0)}%`)}${metric('證據覆蓋',cov==null?'—':`${fmt(cov,0)}%`)}${metric('資料快照',hm(shard.known_at||d.known_at||m?.generated_at))}</div><div class="isd-quality-note"><strong>證據覆蓋 ${cov==null?'—':`${fmt(cov,0)}%`}</strong> 是「這個模式預期需要的評分／決策證據，有多少已取得並可用」，不是「只有 ${cov==null?'部分':`${fmt(cov,0)}%`} 的資料是今天的」。${esc(missText)}</div><details class="isd-diagnostic"><summary>診斷資訊</summary><div>Build：${esc(shard.build_id||d.build_id||'—')}<br>known_at：${esc(shard.known_at||d.known_at||'—')}<br>decision context：${esc(d.decision_context_id||'—')}</div></details></div>`;
  }

  function render(shard,view,box,m){
    const d=shard.decision||{},e=shard.evidence||null,zones=Array.isArray(shard.zones)?shard.zones:[];
    const supports=zones.filter(z=>z.side==='SUPPORT').slice(0,2),resistances=zones.filter(z=>z.side==='RESISTANCE').slice(0,2);
    const [ms,mv]=mainScore(view,d),[lt,tone]=light(view,d);
    const ignite=isIgnition(view);
    const context=ignite?'盤後點火':(VIEW[view]||view);
    const rank=ignite?'點火 #'+(d.ignition_rank??'—'):'排名 #'+(d.opportunity_rank??'—');
    const stage=ignite?(d.ignition_stage||'點火資料待補'):(STAGE[d.lifecycle_stage]||d.lifecycle_stage||'—');
    const action=ignite?(d.ignition_action||'觀察'):(ACTION[d.action_state]||d.action_state||'—');
    box.title.textContent=`${d.code||shard.code} ${d.name||e?.name||''}`.trim();
    box.body.innerHTML=`<div class="isd-context">${esc(context)}詳情 · ${esc(ignite?(d.ignition_stage||'—'):(d.opportunity_bucket||'—'))} · ${esc(rank)}</div>
      <div class="isd-hero"><div><span class="isd-badge">${esc(stage)}</span><h2>${esc(action)}</h2><p>${esc(heroText(view,d))}</p></div><div class="isd-light ${tone}">${esc(lt)}</div></div>
      <div class="isd-score">${scoreTile(ms,mv)}${scoreTile('進場位置',fmt(d.scores?.entry_position_score))}${scoreTile(ignite?'點火信心':'資料信心',`${fmt(ignite?d.ignition_confidence:d.data_confidence,0)}%`)}</div>
      ${freshnessHtml(shard,d,e,m)}
      <div class="isd-section"><h3>支撐 / 壓力</h3><div class="isd-zones">${supports.map(zoneHtml).join('')}${resistances.map(zoneHtml).join('')||'<div class="isd-muted">目前沒有可用支撐／壓力區。</div>'}</div></div>
      <div class="isd-section"><h3>為什麼現在看它</h3>${tags(ignite?(d.ignition_reasons||[]):[...(d.why_now||[]),...(e?.stage_signals||[])],'目前沒有足夠的新理由。')}</div>
      <div class="isd-section"><h3>${ignite?'點火 Gate／卡點':'現在卡在哪裡'}</h3>${tags(ignite?(d.ignition_gate_flags||[]):(d.blockers||[]),'目前沒有額外卡點。')}</div>
      <div class="isd-section"><h3>${view==='close'?'明日升級條件':'升級條件'}</h3>${tags(d.upgrade_conditions||[],'目前尚未形成額外升級條件。')}</div>
      <div class="isd-section"><h3>失效／風險條件</h3>${tags([...(d.risk_flags||[]),...(e?.stage_risks||[]),...(e?.overheat_reasons||[])],'目前沒有額外風險旗標。')}</div>
      <div class="isd-section"><h3>${view==='close'?'盤後技術／籌碼':'即時量價／相對強弱'}</h3>${evidenceHtml(e,view)}</div>
      ${explainHtml(d,e,view)}
      ${qualityHtml(shard,d,m)}`;
  }

  async function openStock(code,view,closeMode){
    activeCloseMode=view==='close'?(closeMode==='ignition'?'ignition':'swing'):'swing';
    const my=++seq,box=ui(code); if(!box)return;
    try{
      const m=await json(`./data/current_manifest.json?t=${Date.now()}`,6000);
      if(my!==seq||!box.dialog.open)return;
      const build=String(m?.active_build_id||'');
      if(!build)throw new Error('active build missing');
      const key=`${build}:${view}:${code}`;
      let shard=cache.get(key);
      if(!shard){
        shard=await json(`./data/builds/${encodeURIComponent(build)}/stock-shards/${encodeURIComponent(view)}/${encodeURIComponent(code)}.json?t=${Date.now()}`,8000);
        cache.set(key,shard);
      }
      if(my!==seq||!box.dialog.open)return;
      if(String(shard?.build_id||'')!==build)throw new Error('build mismatch');
      if(String(shard?.code||'')!==String(code))throw new Error('code mismatch');
      if(String(shard?.view||'')!==String(view))throw new Error('view mismatch');
      if(!shard?.decision)throw new Error('decision missing');
      render(shard,view,box,m);
      document.dispatchEvent(new CustomEvent('radar:detail-rendered',{detail:{code:String(code),view,build}}));
    }catch(err){
      console.error('direct-stock-detail-v2',err);
      if(my!==seq)return;
      box.body.innerHTML=`<div class="isd-error"><b>個股詳情載入失敗</b><br>這次只讀單股小檔，不會用舊資料補猜。<br><small>${esc(err?.message||err)}</small></div>`;
    }
  }

  injectStyle();
  document.addEventListener('radar:open-stock',e=>{
    const code=String(e.detail?.code||'').trim();
    const view=String(e.detail?.view||document.querySelector('.tab.active')?.dataset.view||'intraday');
    if(!code||view==='portfolio')return;
    e.stopImmediatePropagation();
    if(e.cancelable)e.preventDefault();
    const mode=String(e.detail?.closeMode||document.querySelector('[data-close-mode="ignition"].active')?.dataset.closeMode||'swing');
    openStock(code,view,mode);
  },true);
  document.addEventListener('radar:data-reloaded',()=>{cache.clear();seq++;});
  document.addEventListener('close',e=>{if(e.target?.id==='detailDialog')seq++;},true);
})();

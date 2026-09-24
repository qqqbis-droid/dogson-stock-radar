(()=>{
  if(window.__DOGSON_DECISION_FILTERS_V2__) return;
  window.__DOGSON_DECISION_FILTERS_V2__ = true;
  if(typeof render!=='function' || typeof entryDecision!=='function') return;

  const state={
    defaultFocus:true,
    light:null,
    event:null,
    yellowReason:null,
    highQuality:true
  };
  const baseRender=render;
  const baseEntrySummaryHTML=entrySummaryHTML;
  const baseChangeRadarHTML=changeRadarHTML;
  let fullRowsRef=null;

  const n=v=>{const x=Number(v);return Number.isFinite(x)?x:0};
  const stage=r=>typeof stageKey==='function'?stageKey(r?.category):String(r?.category||'');
  function decision(r){try{return entryDecision(r,intraMarket)}catch{return {key:'yellow',wait:[],block:[],score:n(r?.intraday_score??r?.score)}}}

  function coreMisses(r){
    const c=r?.intraday_components||{};
    const mtf=r?.multi_timeframe||{}, rsm=r?.relative_multiframe||{};
    const vwap=n(r?.vwap_dist), pos=n(r?.range_position_pct||50);
    return [
      n(r?.intraday_score??r?.score)<70,
      n(c.price_structure)<20,
      n(c.flow_volume)<14,
      n(c.relative_strength)<8,
      n(c.sector)<8,
      n(c.liquidity_risk)<6,
      vwap<-.5||vwap>2.5,
      pos<45||pos>90,
      String(mtf.state||'')==='CONFLICT'||String(mtf.state||'')==='WEAK',
      String(rsm.status||'')==='LAGGING'
    ].filter(Boolean).length;
  }

  function highQuality(r){
    const d=decision(r),c=r?.intraday_components||{},s=stage(r);
    if(d.key==='green') return true;
    if(d.key!=='yellow') return false;
    if(['轉弱警戒','結構失效','過熱不追'].includes(s)) return false;
    const score=n(r?.intraday_score??r?.score);
    const pattern=String(r?.execution_pattern||'');
    const patternOK=['量縮回踩','量增上攻','承接整理'].includes(pattern)||Boolean(r?.break3)||Boolean(r?.trend5);
    return score>=58 && n(c.price_structure)>=15 && n(c.flow_volume)>=10 && n(c.relative_strength)>=6 && n(c.sector)>=6 && n(c.liquidity_risk)>=5 && coreMisses(r)<=4 && patternOK;
  }

  function yellowReason(r){
    const d=decision(r),c=r?.intraday_components||{},v=n(r?.vwap_dist),pos=n(r?.range_position_pct||50);
    if(d.key!=='yellow') return null;
    const mtf=String(r?.multi_timeframe?.state||'');
    if(v<-.5) return 'vwap';
    if(v>2.5||pos>90) return 'pullback';
    if(mtf==='CONFLICT'||mtf==='WEAK'||mtf==='MIXED') return '60k';
    if(n(c.sector)<8) return 'sector';
    if(coreMisses(r)<=1) return 'one';
    return 'other';
  }

  function eventMatch(r,key){
    const t=r?.today_transitions||{}, ev=Array.isArray(r?.change_events)?r.change_events:[];
    if(key==='setup') return !!t.entered_setup;
    if(key==='launch') return !!t.entered_launch;
    if(key==='improving') return r?.today_direction==='一路改善';
    if(key==='restrengthening') return r?.today_direction==='重新轉強';
    if(key==='heldweak') return !!t.became_weak && (typeof held==='function'?held(r.code):true);
    if(key==='overheat') return !!t.became_overheat;
    if(key==='sectorToday'){
      const names=new Set(((changeRadar?.today?.sector_accel)||[]).map(x=>String(x.sector||'')));
      return names.has(String(r?.sector_group||r?.industry_name||r?.industry||''));
    }
    const map={turnStrong:'turn_strong',turnWeak:'turn_weak',breakout:'breakout',vwapReclaim:'vwap_reclaim',sectorNow:'sector_accel'};
    return ev.some(x=>x?.type===map[key]);
  }

  function rowMatch(r){
    const d=decision(r);
    if(state.event && !eventMatch(r,state.event)) return false;
    if(state.event && state.highQuality && !highQuality(r)) return false;
    if(state.light && d.key!==state.light) return false;
    if(state.light==='yellow' && state.yellowReason && yellowReason(r)!==state.yellowReason) return false;
    if(!state.event && !state.light && state.defaultFocus){
      return d.key==='green' || (d.key==='yellow' && highQuality(r));
    }
    return true;
  }

  entrySummaryHTML=function(){
    if(!fullRowsRef) return baseEntrySummaryHTML();
    const cur=intraRows;intraRows=fullRowsRef;
    try{return baseEntrySummaryHTML()}finally{intraRows=cur}
  };
  changeRadarHTML=function(){
    if(!fullRowsRef) return baseChangeRadarHTML();
    const cur=intraRows;intraRows=fullRowsRef;
    try{return baseChangeRadarHTML()}finally{intraRows=cur}
  };

  function clearSelection(){state.defaultFocus=false;state.light=null;state.event=null;state.yellowReason=null}
  function rerender(){try{render()}catch(e){console.warn('decision filter render',e)}}

  function addStyles(){
    if(document.getElementById('dogsonDecisionFilterStyles'))return;
    const s=document.createElement('style');s.id='dogsonDecisionFilterStyles';s.textContent=`
      .entrycount,.changecount{cursor:pointer;transition:.15s}.entrycount:active,.changecount:active{transform:scale(.98)}
      .entrycount.df-on,.changecount.df-on{outline:2px solid #63a4ff;outline-offset:1px;background:#172b42}
      .decision-filterbar{display:flex;gap:6px;overflow:auto;margin-top:9px;padding-bottom:2px}
      .decision-filterbtn{white-space:nowrap;border:1px solid #334052;background:#111823;color:#cbd6e6;border-radius:999px;padding:6px 9px;font-size:10px;font-weight:800}
      .decision-filterbtn.on{border-color:#4d8ac7;background:#17304a;color:#cde6ff}
      .decision-filter-note{font-size:10px;color:#9ba5b6;margin-top:7px;line-height:1.5}
      .yellow-reasons{display:flex;gap:6px;overflow:auto;margin-top:7px}
    `;document.head.appendChild(s);
  }

  const eventMap=[
    ['今日新進蓄勢','setup'],['今日新進剛啟動','launch'],['一路改善','improving'],['重新轉強','restrengthening'],
    ['庫存今日轉弱','heldweak'],['今日轉過熱','overheat'],['今日族群加速','sectorToday'],
    ['5分轉強','turnStrong'],['5分轉弱','turnWeak'],['剛突破','breakout'],['剛站回VWAP','vwapReclaim'],['族群剛加速','sectorNow']
  ];

  function enhanceEntry(){
    const box=document.querySelector('#entrySummary .entrysummary')||document.querySelector('.entrysummary');if(!box)return;
    const counts=[...box.querySelectorAll('.entrycount')];
    if(counts.length>=3 && typeof mode!=='undefined' && mode==='intraday'){
      const keys=['green','yellow','red'];
      counts.slice(0,3).forEach((el,i)=>{
        el.classList.toggle('df-on',state.light===keys[i]);
        el.onclick=()=>{state.defaultFocus=false;state.event=null;state.light=state.light===keys[i]?null:keys[i];state.yellowReason=null;rerender()};
      });
    }
    let bar=box.querySelector('.decision-filterbar');
    if(!bar){bar=document.createElement('div');bar.className='decision-filterbar';box.appendChild(bar)}
    bar.innerHTML=`<button class="decision-filterbtn ${state.defaultFocus&&!state.light&&!state.event?'on':''}" data-df="focus">✨ 綠燈＋高品質黃</button><button class="decision-filterbtn ${!state.defaultFocus&&!state.light&&!state.event?'on':''}" data-df="all">全部</button>`;
    bar.querySelector('[data-df="focus"]')?.addEventListener('click',()=>{state.defaultFocus=true;state.light=null;state.event=null;state.yellowReason=null;rerender()});
    bar.querySelector('[data-df="all"]')?.addEventListener('click',()=>{clearSelection();rerender()});

    let yr=box.querySelector('.yellow-reasons');
    if(state.light==='yellow'){
      if(!yr){yr=document.createElement('div');yr.className='yellow-reasons';box.appendChild(yr)}
      const rs=[['one','差一個條件'],['pullback','等回踩'],['vwap','等VWAP'],['60k','60K未跟上'],['sector','族群不足'],['other','其他確認']];
      yr.innerHTML=rs.map(([k,l])=>`<button class="decision-filterbtn ${state.yellowReason===k?'on':''}" data-yr="${k}">${l}</button>`).join('');
      yr.querySelectorAll('[data-yr]').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.yr;state.yellowReason=state.yellowReason===k?null:k;rerender()}));
    }else if(yr)yr.remove();

    let note=box.querySelector('.decision-filter-note');if(!note){note=document.createElement('div');note.className='decision-filter-note';box.appendChild(note)}
    note.textContent=state.defaultFocus&&!state.light&&!state.event?'目前預設：只顯示 🟢 可試單＋高品質 🟡；紅燈不佔注意力。':'點三燈或上方事件即可直接篩選；再次點擊可取消。';
  }

  function enhanceChange(){
    const box=document.getElementById('changebox');if(!box)return;
    const chips=[...box.querySelectorAll('.changecount')];
    chips.forEach(el=>{
      const txt=el.textContent||'';const found=eventMap.find(([label])=>txt.includes(label));if(!found)return;
      const key=found[1];el.classList.toggle('df-on',state.event===key);
      el.onclick=()=>{state.defaultFocus=false;state.light=null;state.yellowReason=null;state.event=state.event===key?null:key;rerender()};
    });
    let bar=box.querySelector('.decision-filterbar.event-quality');
    if(!bar){bar=document.createElement('div');bar.className='decision-filterbar event-quality';const top=box.querySelector('.changetop');(top||box).insertAdjacentElement('afterend',bar)}
    bar.innerHTML=`<button class="decision-filterbtn ${state.highQuality?'on':''}" data-quality="1">✨ 高品質二次篩選 ${state.highQuality?'ON':'OFF'}</button>${state.event?'<button class="decision-filterbtn on" data-clear-event="1">清除事件篩選</button>':''}`;
    bar.querySelector('[data-quality]')?.addEventListener('click',()=>{state.highQuality=!state.highQuality;if(state.event)rerender();else enhance()});
    bar.querySelector('[data-clear-event]')?.addEventListener('click',()=>{state.event=null;state.defaultFocus=true;rerender()});
  }

  function enhance(){addStyles();enhanceEntry();enhanceChange()}

  render=function(){
    if(typeof mode==='undefined'||mode!=='intraday'){
      baseRender();setTimeout(enhance,0);return;
    }
    const full=Array.isArray(intraRows)?intraRows:[];fullRowsRef=full;
    const filtered=full.filter(rowMatch);const cur=intraRows;intraRows=filtered;
    try{baseRender()}finally{intraRows=cur;fullRowsRef=null}
    setTimeout(enhance,0);
  };

  addStyles();
  setTimeout(()=>{try{render()}catch{}},50);
})();

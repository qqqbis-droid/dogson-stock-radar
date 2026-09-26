(()=>{
  if(window.__DOGSON_CARD_V166__) return;
  window.__DOGSON_CARD_V166__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const txt=(s,r=document)=>$(s,r)?.textContent?.trim()||'';
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/^[🟢🟡🔴🌱🔥⚠️🚫🚂✨⭐💼🔵✅]+\s*/,'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  const short=(s,n=58)=>{s=String(s||'').replace(/\s+/g,' ').trim().split(/[。；;]/)[0];return s.length>n?s.slice(0,n-1)+'…':s};
  let busy=false,timer=null;

  function viewState(){
    let m='intraday',p=false;
    try{if(typeof mode!=='undefined')m=mode||m}catch{}
    try{if(typeof portfolioOnly!=='undefined')p=!!portfolioOnly}catch{}
    return{m,p};
  }
  function codeOf(card){return String(card?.dataset?.code||txt('.code',card)||'').trim();}
  function held(card){
    const code=codeOf(card);
    try{if(code&&typeof holding==='function')return !!holding(code)}catch{}
    return !!($('.portfoliobox',card)||$('.portfolio-decision',card));
  }
  function portfolioView(){
    const s=viewState();
    if(s.p)return true;
    return document.documentElement.classList.contains('dogson-portfolio-view');
  }
  function canonicalRow(card){
    const code=codeOf(card);if(!code)return null;
    const s=viewState();let arr=[];
    try{
      if(Array.isArray(window.DOGSON_FILTERED_ROWS)&&window.DOGSON_FILTERED_ROWS.some(r=>String(r?.code)===code))arr=window.DOGSON_FILTERED_ROWS;
      else if(s.m==='daytrade'&&Array.isArray(daytradeRows))arr=daytradeRows;
      else if(s.m==='close'&&Array.isArray(closeRows))arr=closeRows;
      else if(s.m==='intraday'&&window.DOGSON_INTRADAY_LIVE_READY===false&&Array.isArray(closeRows))arr=closeRows;
      else if(Array.isArray(intraRows))arr=intraRows;
    }catch{}
    return arr.find(r=>String(r?.code)===code)||null;
  }
  function canonicalStage(r){
    if(!r)return'';
    try{if(typeof stageKey==='function')return stageKey(r.category)||''}catch{}
    return clean(r.category||'');
  }
  function canonicalEntry(r){
    if(!r)return null;
    try{
      if(typeof entryDecision==='function'){
        let mkt;
        try{mkt=(window.DOGSON_INTRADAY_LIVE_READY===false&&typeof closeMarket!=='undefined')?closeMarket:(typeof intraMarket!=='undefined'?intraMarket:undefined)}catch{}
        return entryDecision(r,mkt);
      }
    }catch{}
    return null;
  }
  function source(card,cls){
    return $(`.dogson-card-details .${cls}`,card)||$$(`.${cls}`,card).find(x=>!x.closest('.dogson-action-strip-v164')&&!x.closest('.dogson-card-brief'))||$(`.${cls}`,card);
  }

  function shortLabel(type,text){
    let s=clean(text);
    if(type==='quality'){
      s=s.replace(/^動能\s*[：:]\s*/,'').replace(/^波段\s*[：:]\s*/,'').replace(/^當沖\s*[：:]\s*/,'');
      if(s==='強')s='波段強';
    }
    return s||clean(text)||text;
  }

  function canonicalConclusion(card){
    const s=viewState(),r=canonicalRow(card);
    if(s.p||s.m!=='intraday'||!r)return'';
    const st=clean(canonicalStage(r));
    const d=canonicalEntry(r)||{};
    const en=`${d.icon||''} ${d.label||''}`.trim();
    const eh=short(d.headline||'',48);
    const sr=short(r.stage_reason||'',48);
    const wait=short((d.wait||[])[0]||'',42);
    const blk=short((d.block||[])[0]||'',42);
    if(/過熱/.test(st))return '結構仍強但短線偏熱，現在不適合追價'+(sr?'；'+sr:'');
    if(/失效/.test(st))return '結構已失效，先不做新的進場'+(blk?'；'+blk:eh?'；'+eh:'');
    if(/轉弱/.test(st))return '短線轉弱，先等結構重新站穩'+(sr?'；'+sr:'');
    if(/不做|先不進/.test(en)||/🔴/.test(en))return '目前先不做'+(blk?'；'+blk:eh?'；'+eh:'');
    if(/可試|可觀察/.test(en)||/🟢/.test(en))return (/剛啟動/.test(st)?'剛啟動成立，條件同步':'條件同步，可列入觀察試單')+(eh?'；'+eh:'');
    if(/等確認/.test(en)||/🟡/.test(en)){
      const why=wait||eh||sr;
      return (/蓄勢/.test(st)?'仍在蓄勢，先等發動條件補齊':/回踩/.test(st)?'回踩整理中，等止穩再決定':'方向未壞，先等確認')+(why?'；'+why:'');
    }
    if(/蓄勢/.test(st))return '仍在蓄勢，可先蹲車觀察'+(sr?'；'+sr:'');
    if(/剛啟動/.test(st))return '剛啟動，先確認追價風險'+(sr?'；'+sr:'');
    if(/回踩/.test(st))return '回踩整理中，重點看支撐是否守住'+(sr?'；'+sr:'');
    if(/趨勢|持有/.test(st))return '趨勢結構仍在，短線震盪先看是否破壞結構'+(sr?'；'+sr:'');
    return eh||sr||'點開查看完整判讀。';
  }

  function marketConclusion(card){
    const canonical=canonicalConclusion(card);if(canonical)return canonical;
    const st=clean(source(card,'cat')?.textContent||'');
    const en=source(card,'entrylight')?.textContent?.trim()||'';
    const eh=short(txt('.entryheadline',card),48);
    const sr=short(txt('.stagereason',card),48);
    const wait=short(txt('.entrywhy .wait',card),42);
    const blk=short(txt('.entrywhy .block',card),42);
    if(/過熱/.test(st))return '結構仍強但短線偏熱，現在不適合追價'+(sr?'；'+sr:'');
    if(/失效/.test(st))return '結構已失效，先不做新的進場'+(blk?'；'+blk:eh?'；'+eh:'');
    if(/轉弱/.test(st))return '短線轉弱，先等結構重新站穩'+(sr?'；'+sr:'');
    if(/不做|先不進/.test(en)||/🔴/.test(en))return '目前先不做'+(blk?'；'+blk:eh?'；'+eh:'');
    if(/可試|可觀察/.test(en)||/🟢/.test(en))return (/剛啟動/.test(st)?'剛啟動成立，條件同步':'條件同步，可列入觀察試單')+(eh?'；'+eh:'');
    if(/等確認/.test(en)||/🟡/.test(en)){
      const why=wait||eh||sr;
      return (/蓄勢/.test(st)?'仍在蓄勢，先等發動條件補齊':/回踩/.test(st)?'回踩整理中，等止穩再決定':'方向未壞，先等確認')+(why?'；'+why:'');
    }
    if(/蓄勢/.test(st))return '仍在蓄勢，可先蹲車觀察'+(sr?'；'+sr:'');
    if(/剛啟動/.test(st))return '剛啟動，先確認追價風險'+(sr?'；'+sr:'');
    if(/回踩/.test(st))return '回踩整理中，重點看支撐是否守住'+(sr?'；'+sr:'');
    if(/趨勢|持有/.test(st))return '趨勢結構仍在，短線震盪先看是否破壞結構'+(sr?'；'+sr:'');
    return eh||sr||'點開查看完整判讀。';
  }

  function ensureBrief(card){
    let brief=$('.dogson-card-brief',card);
    if(brief)return brief;
    brief=document.createElement('div');brief.className='dogson-card-brief';
    const anchor=$('.dogson-action-strip-v164',card)||$('.top',card);
    anchor?.after(brief);
    return brief;
  }
  function normalBrief(card){
    const brief=ensureBrief(card);if(!brief)return;
    brief.classList.remove('portfolio-brief');
    const line=marketConclusion(card);
    const html=`<div class="dogson-card-headline">${esc(line)}</div>`;
    if(brief.dataset.v166Html!==html||brief.innerHTML!==html){brief.innerHTML=html;brief.dataset.v166Html=html;}
  }

  function canonicalSignalSpec(card){
    const s=viewState(),r=canonicalRow(card);
    if(s.p||s.m!=='intraday'||!r)return null;
    const st=canonicalStage(r)||'觀察';
    const d=canonicalEntry(r);
    const q=String(r.quality_label||'一般').trim()||'一般';
    let stageCls='cat';try{if(typeof cls==='function')stageCls+=' '+cls(r.category)}catch{}
    let qCls='quality';try{if(typeof qualityCls==='function')qCls+=' '+qualityCls(q)}catch{}
    const out=[{cls:'cat',type:'stage',text:st,full:st,className:stageCls,canonical:true}];
    if(d)out.push({cls:'entrylight',type:'entry',text:shortLabel('entry',`${d.icon||''} ${d.label||''}`),full:`${d.icon||''} ${d.label||''}`.trim(),className:`entrylight ${d.key||'yellow'}`,canonical:true});
    out.push({cls:'quality',type:'quality',text:shortLabel('quality',`動能：${q}`),full:`動能：${q}`,className:qCls,canonical:true});
    return out;
  }
  function signalSpec(card){
    const canonical=canonicalSignalSpec(card);if(canonical)return canonical;
    return [['cat','stage'],['entrylight','entry'],['quality','quality']].map(([cls,type])=>{
      const src=source(card,cls);if(!src)return null;
      return {cls,type,text:shortLabel(type,src.textContent||''),full:src.textContent||'',canonical:false};
    }).filter(Boolean);
  }
  function makeSignal(card,item){
    let chip;
    if(item.canonical){
      chip=document.createElement('span');chip.className=item.className||item.cls;
    }else{
      const src=source(card,item.cls);if(!src)return null;
      chip=src.cloneNode(false);
      chip.removeAttribute('style');chip.removeAttribute('id');
      [...chip.attributes].forEach(a=>{if(/^data-v163|^data-v164|^data-v166/.test(a.name))chip.removeAttribute(a.name)});
    }
    chip.textContent=item.text||shortLabel(item.type,item.full||'');
    chip.classList.add('dogson-signal-btn-v164','dogson-signal-btn-v166');
    chip.dataset.dogsonQuick=item.type;
    chip.dataset.v164Full=item.full||chip.textContent||'';
    chip.setAttribute('role','button');chip.setAttribute('tabindex','0');chip.setAttribute('aria-haspopup','dialog');
    return chip;
  }

  function normalizePortfolioButton(card,actions){
    const btns=$$('.portfolio-mini',card);
    const p=btns.find(x=>x===actions?.querySelector('.portfolio-mini'))||btns[0];
    if(!p)return;
    if(actions&&p.parentElement!==actions)actions.appendChild(p);
    p.classList.add('dogson-portfolio-btn-v164');
    p.classList.remove('dogson-portfolio-action-v163');
    const isHeld=held(card);
    p.classList.toggle('held',isHeld);
    const label=isHeld?'✓ 庫存':'＋ 庫存';
    if(p.textContent!==label)p.textContent=label;
    p.setAttribute('aria-label',isHeld?'編輯庫存':'加入庫存');
    if(actions)$$(':scope>.portfolio-mini',actions).slice(1).forEach(x=>x.remove());
  }

  function ensureStrip(card){
    const strips=$$('.dogson-action-strip-v164',card);
    let keep=strips[0];strips.slice(1).forEach(x=>x.remove());
    if(!keep){
      keep=document.createElement('div');keep.className='dogson-action-strip-v164';
      keep.innerHTML='<div class="dogson-signal-buttons-v164"></div><div class="dogson-card-actions-v164"></div>';
      $('.top',card)?.after(keep);
    }
    if(!$('.dogson-signal-buttons-v164',keep))keep.prepend(Object.assign(document.createElement('div'),{className:'dogson-signal-buttons-v164'}));
    if(!$('.dogson-card-actions-v164',keep))keep.append(Object.assign(document.createElement('div'),{className:'dogson-card-actions-v164'}));
    return keep;
  }
  function dedupeStrip(card){
    const keep=ensureStrip(card);if(!keep)return null;
    const signals=$('.dogson-signal-buttons-v164',keep);if(!signals)return keep;
    const spec=signalSpec(card);
    const sig=spec.map(x=>`${x.type}|${x.text}|${x.full}|${x.className||''}`).join('||');
    if(signals.dataset.v166Sig!==sig||signals.children.length!==spec.length){
      const frag=document.createDocumentFragment();
      spec.forEach(item=>{const chip=makeSignal(card,item);if(chip)frag.appendChild(chip)});
      signals.replaceChildren(frag);
      signals.dataset.v166Sig=sig;
    }
    const actions=$('.dogson-card-actions-v164',keep);
    if(actions)normalizePortfolioButton(card,actions);
    return keep;
  }

  function metric(card,label){
    const ms=$$('.portfolio-metric',card);
    const m=ms.find(x=>txt('.portfolio-metric-l',x).includes(label));
    return m?txt('.portfolio-metric-v',m):'';
  }

  function portfolioData(card){
    const badge=clean(txt('.portfolio-decision-badge',card));
    const status=clean(txt('.portfolio-status',card));
    const head=short(txt('.portfolio-decision-head',card),74);
    const reason=short(txt('.portfolio-reason',card).replace('進場理由','').replace(/^[:：]\s*/,''),54);
    const cost=metric(card,'平均成本');
    const shares=metric(card,'持有股數');
    return{badge,status,head,reason,cost,shares};
  }

  function portfolioAddon(card){
    let box=$('.dogson-portfolio-addon-v166',card);
    if(!held(card)||!portfolioView()){box?.remove();return;}
    const p=portfolioData(card);
    if(!box){
      box=document.createElement('section');box.className='dogson-portfolio-addon-v166';
      const live=$('.livequote',card),brief=$('.dogson-card-brief',card);
      (live||brief)?.after(box);
    }
    const facts=[p.cost?`成本 <b>${esc(p.cost)}</b>`:'',p.shares?`持有 <b>${esc(p.shares)}</b>`:''].filter(Boolean).join('<span class="dogson-portfolio-dot-v166">·</span>');
    const html=`<div class="dogson-portfolio-addon-top-v166"><div class="dogson-portfolio-addon-title-v166">💼 庫存追蹤</div>${p.badge?`<span class="dogson-portfolio-addon-badge-v166">${esc(p.badge)}</span>`:''}</div>${facts?`<div class="dogson-portfolio-addon-facts-v166">${facts}</div>`:''}${p.head?`<div class="dogson-portfolio-addon-head-v166">${esc(p.head)}</div>`:''}${p.status?`<div class="dogson-portfolio-addon-status-v166">理由狀態：${esc(p.status)}</div>`:''}${p.reason?`<div class="dogson-portfolio-addon-reason-v166">原始理由：${esc(p.reason)}</div>`:''}`;
    if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html;}
  }

  function reasonTexts(card){
    const out=[];const add=t=>{t=clean(t);if(!t||t.length>28||out.includes(t))return;out.push(t)};
    $$('.entrywhy span:not(.block),.stagechip:not(.risk)',card).forEach(x=>add(x.textContent));
    if(out.length<2)$$('.entrymeta span',card).forEach(x=>{/VWAP|結構|相對強弱|量價|族群|60K|5分K|流動性/.test(clean(x.textContent))&&add(x.textContent)});
    return out.slice(0,4);
  }

  function ensureReasons(card){
    const details=$('.dogson-card-details',card);if(!details)return;
    const rs=reasonTexts(card);if(!rs.length)return;
    let box=$('.dogson-key-reasons',card);
    if(!box){box=document.createElement('div');box.className='dogson-key-reasons';details.before(box);}
    const html=`<div class="dogson-key-title">關鍵理由</div><div class="dogson-key-list">${rs.map(x=>`<span class="dogson-key-btn-v164" data-dogson-quick="reason" role="button" tabindex="0" aria-haspopup="dialog">✓ ${esc(x)}</span>`).join('')}</div>`;
    if(box.dataset.v166Html!==html){box.innerHTML=html;box.dataset.v166Html=html;}
  }

  function card(card){
    card.classList.add('dogson-v166-card');
    dedupeStrip(card);
    normalBrief(card);
    portfolioAddon(card);
    ensureReasons(card);
  }

  function run(){if(busy)return;busy=true;try{$$('#cards .card').forEach(card)}finally{busy=false}}
  function schedule(delay=95){if(busy)return;clearTimeout(timer);timer=setTimeout(run,delay)}
  function start(){
    run();
    const root=$('#cards');
    const obs=new MutationObserver(()=>schedule(95));
    if(root)obs.observe(root,{subtree:true,childList:true,characterData:true});
    document.addEventListener('click',e=>{
      if(!e.target.closest?.('[data-portfolio-save],[data-portfolio-remove]'))return;
      [25,90,180,360,720].forEach(ms=>setTimeout(run,ms));
    },true);
    setTimeout(run,220);setTimeout(run,760);setInterval(run,3500);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
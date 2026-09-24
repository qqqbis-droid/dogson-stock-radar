(()=>{
  if(window.__DOGSON_CARD_V166__) return;
  window.__DOGSON_CARD_V166__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const txt=(s,r=document)=>$(s,r)?.textContent?.trim()||'';
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/^[🟢🟡🔴🌱🔥⚠️🚫🚂✨⭐💼🔵✅]+\s*/,'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const short=(s,n=58)=>{s=String(s||'').replace(/\s+/g,' ').trim().split(/[。；;]/)[0];return s.length>n?s.slice(0,n-1)+'…':s};
  let busy=false,timer=null;

  function held(card){return !!($('.portfoliobox',card)||$('.portfolio-decision',card));}
  function portfolioView(){
    try{if(typeof portfolioOnly!=='undefined')return !!portfolioOnly}catch{}
    return document.documentElement.classList.contains('dogson-portfolio-view');
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

  function marketConclusion(card){
    const st=clean(source(card,'cat')?.textContent||'');
    const en=source(card,'entrylight')?.textContent?.trim()||'';
    const eh=short(txt('.entryheadline',card),48);
    const sr=short(txt('.stagereason',card),48);
    const wait=short(txt('.entrywhy .wait',card),42);
    const blk=short(txt('.entrywhy .block',card),42);
    if(/過熱/.test(st))return '結構仍強但短線偏熱，現在不適合追價'+(sr?'；'+sr:'');
    if(/失效/.test(st))return '結構已失效，先不做新的進場'+(blk?'；'+blk:'');
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

  function normalBrief(card){
    const brief=$('.dogson-card-brief',card);if(!brief)return;
    brief.classList.remove('portfolio-brief');
    const line=marketConclusion(card);
    const html=`<div class="dogson-card-headline">${esc(line)}</div>`;
    if(brief.dataset.v166Html!==html||brief.innerHTML!==html){brief.innerHTML=html;brief.dataset.v166Html=html;}
  }

  function cloneSignal(card,cls,type){
    const src=source(card,cls);if(!src)return null;
    const chip=src.cloneNode(false);
    chip.removeAttribute('style');chip.removeAttribute('id');
    [...chip.attributes].forEach(a=>{if(/^data-v163|^data-v164|^data-v166/.test(a.name))chip.removeAttribute(a.name)});
    chip.textContent=shortLabel(type,src.textContent||'');
    chip.classList.add('dogson-signal-btn-v164','dogson-signal-btn-v166');
    chip.dataset.dogsonQuick=type;
    chip.dataset.v164Full=src.textContent||'';
    chip.setAttribute('role','button');chip.setAttribute('tabindex','0');chip.setAttribute('aria-haspopup','dialog');
    return chip;
  }

  function signalSpec(card){
    return [['cat','stage'],['entrylight','entry'],['quality','quality']].map(([cls,type])=>{
      const src=source(card,cls);if(!src)return null;
      return {cls,type,text:shortLabel(type,src.textContent||''),full:src.textContent||''};
    }).filter(Boolean);
  }

  function normalizePortfolioButton(card,actions){
    const btns=$$('.portfolio-mini',card);
    const p=btns.find(x=>x===actions?.querySelector('.portfolio-mini'))||btns[0];
    if(!p)return;
    if(actions&&p.parentElement!==actions)actions.appendChild(p);
    p.classList.add('dogson-portfolio-btn-v164');
    p.classList.remove('dogson-portfolio-action-v163');
    const isHeld=p.classList.contains('held')||/已持有|已加入|✓/.test(p.textContent||'')||held(card);
    const label=isHeld?'✓ 庫存':'＋ 庫存';
    if(p.textContent!==label)p.textContent=label;
    p.setAttribute('aria-label',isHeld?'編輯庫存':'加入庫存');
    if(actions)$$(':scope>.portfolio-mini',actions).slice(1).forEach(x=>x.remove());
  }

  function dedupeStrip(card){
    const strips=$$('.dogson-action-strip-v164',card);
    if(!strips.length)return null;
    const keep=strips[0];strips.slice(1).forEach(x=>x.remove());
    const signals=$('.dogson-signal-buttons-v164',keep);if(!signals)return keep;
    const spec=signalSpec(card);
    const sig=spec.map(x=>`${x.type}|${x.text}|${x.full}`).join('||');
    if(signals.dataset.v166Sig!==sig||signals.children.length!==spec.length){
      const frag=document.createDocumentFragment();
      spec.forEach(({cls,type})=>{const chip=cloneSignal(card,cls,type);if(chip)frag.appendChild(chip)});
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
    normalBrief(card);
    dedupeStrip(card);
    portfolioAddon(card);
    ensureReasons(card);
  }

  function run(){if(busy)return;busy=true;try{$$('#cards .card').forEach(card)}finally{busy=false}}
  function schedule(delay=80){if(busy)return;clearTimeout(timer);timer=setTimeout(run,delay)}
  function start(){
    run();
    const root=$('#cards');
    const obs=new MutationObserver(()=>schedule(70));
    if(root)obs.observe(root,{subtree:true,childList:true,characterData:true});
    document.addEventListener('click',e=>{
      if(!e.target.closest?.('[data-portfolio-save],[data-portfolio-remove]'))return;
      [40,120,280,650].forEach(ms=>setTimeout(run,ms));
    },true);
    setTimeout(run,250);setTimeout(run,900);setInterval(run,4000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

(()=>{
  if(window.__DOGSON_CARD_V164__) return;
  window.__DOGSON_CARD_V164__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/^[🟢🟡🔴🌱🔥⚠️🚫🚂✨⭐💼]+\s*/,'').replace(/\s+/g,' ').trim();
  let busy=false,timer=null;

  function shortLabel(type,text){
    let s=clean(text);
    if(type==='quality'){
      s=s.replace(/^動能\s*[：:]\s*/,'').replace(/^波段\s*[：:]\s*/,'').replace(/^當沖\s*[：:]\s*/,'');
      if(s==='強')s='波段強';
      if(s==='一般')s='一般';
    }
    if(type==='entry'){
      s=s.replace(/^🟢\s*/,'').replace(/^🟡\s*/,'').replace(/^🔴\s*/,'');
    }
    return s||text;
  }

  function ensureSheet(){
    let back=$('#dogsonQuickDetailBack');
    if(back)return back;
    back=document.createElement('div');
    back.id='dogsonQuickDetailBack';
    back.className='dogson-quick-detail-back';
    back.hidden=true;
    back.innerHTML=`<section class="dogson-quick-detail" role="dialog" aria-modal="true" aria-labelledby="dogsonQuickDetailTitle">
      <div class="dogson-quick-detail-handle" aria-hidden="true"></div>
      <div class="dogson-quick-detail-top"><div><div class="dogson-quick-detail-kicker">快速查看</div><div id="dogsonQuickDetailTitle" class="dogson-quick-detail-title">詳細資料</div></div><button type="button" class="dogson-quick-detail-close" aria-label="關閉">×</button></div>
      <div class="dogson-quick-detail-body"></div>
    </section>`;
    document.body.appendChild(back);
    back.addEventListener('click',e=>{if(e.target===back||e.target.closest('.dogson-quick-detail-close'))closeSheet()});
    return back;
  }

  function closeSheet(){
    const back=$('#dogsonQuickDetailBack');if(!back||back.hidden)return;
    back.classList.remove('show');
    setTimeout(()=>{back.hidden=true;document.body.classList.remove('dogson-sheet-open')},150);
  }

  function cloneClean(node){
    if(!node)return null;
    const c=node.cloneNode(true);
    c.removeAttribute('id');
    c.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));
    c.querySelectorAll('button,a,input,select,textarea').forEach(x=>{x.setAttribute('tabindex','-1');if(x.tagName==='BUTTON')x.disabled=true});
    return c;
  }

  function stockTitle(card){
    const n=$('.name',card);let name='個股';
    if(n){const t=[...n.childNodes].find(x=>x.nodeType===Node.TEXT_NODE)?.textContent||n.textContent;name=clean(t)}
    const code=clean($('.code',card)?.textContent||'');
    return code?`${name} ${code}`:name;
  }

  function panel(card,type,label){
    const wrap=document.createElement('div');wrap.className='dogson-quick-detail-stack';
    const intro=document.createElement('div');intro.className='dogson-quick-detail-intro';
    let nodes=[];
    if(type==='stage'){
      intro.textContent='生命週期說明：這裡直接顯示為什麼目前被判定在這個階段，以及支持／風險條件。';
      nodes=[$('.stagebox',card)];
    }else if(type==='entry'){
      intro.textContent='進場判讀：這裡直接顯示目前為什麼是「可觀察／等確認／先不進」，以及還差哪些條件。';
      nodes=[$('.entrybox',card),$('.mtfbox',card)];
    }else if(type==='quality'){
      intro.textContent='動能與品質：拆解目前分數、短線動能與多時間框架，用來理解強弱，不代表上漲機率。';
      nodes=[$('.parts.intradayparts',card)||$('.parts.closeparts',card)||$('.parts',card),$('.metrics',card),$('.mtfbox',card)];
    }else if(type==='portfolio'){
      intro.textContent='庫存管理：以原始進場理由、持有理由與結構失效條件為核心。';
      nodes=[$('.portfolio-decision',card)||$('.portfoliobox',card)];
    }else{
      intro.innerHTML=`你點的是「<b>${clean(label)||'關鍵條件'}</b>」，以下直接顯示最相關的判讀。`;
      const key=clean(label).replace(/^關鍵理由\s*/,'');
      const hit=$$('.stagechip,.entrywhy span,.entrymeta span,.reason,.mtfcell,.metric,.part',card).find(x=>clean(x.textContent).includes(key)||key.includes(clean(x.textContent)));
      nodes=[hit?.closest('.stagebox,.entrybox,.mtfbox,.daytradebox,.portfolio-decision,.portfoliobox')||$('.entrybox',card)||$('.stagebox',card)];
    }
    wrap.append(intro);
    const seen=new Set();
    nodes.filter(Boolean).forEach(n=>{if(seen.has(n))return;seen.add(n);const c=cloneClean(n);if(c)wrap.append(c)});
    if(wrap.children.length===1){const e=document.createElement('div');e.className='dogson-quick-detail-empty';e.textContent='目前沒有更多細節。';wrap.append(e)}
    return wrap;
  }

  function showSheet(card,type,label){
    const back=ensureSheet(),body=$('.dogson-quick-detail-body',back),title=$('.dogson-quick-detail-title',back),kicker=$('.dogson-quick-detail-kicker',back);
    title.textContent=`${stockTitle(card)}｜${clean(label)||'詳細資料'}`;
    kicker.textContent=type==='stage'?'生命週期詳細':type==='entry'?'進場判讀詳細':type==='quality'?'動能與品質詳細':type==='portfolio'?'庫存判讀詳細':'條件詳細';
    body.innerHTML='';body.append(panel(card,type,label));
    back.hidden=false;document.body.classList.add('dogson-sheet-open');requestAnimationFrame(()=>back.classList.add('show'));
  }

  function actionStrip(card){
    const top=$('.top',card),brief=$('.dogson-card-brief',card);if(!top||!brief)return;
    let strip=$('.dogson-action-strip-v164',card);
    if(!strip){
      strip=document.createElement('div');strip.className='dogson-action-strip-v164';
      strip.innerHTML='<div class="dogson-signal-buttons-v164"></div><div class="dogson-card-actions-v164"></div>';
      top.after(strip);
    }
    const signals=$('.dogson-signal-buttons-v164',strip),actions=$('.dogson-card-actions-v164',strip);
    const badgeBox=$('.dogson-card-badges',brief);
    const map=[['cat','stage'],['entrylight','entry'],['quality','quality']];
    map.forEach(([cls,type])=>{
      let chip=$('.'+cls,brief)||$('.'+cls,strip);
      if(!chip)return;
      if(chip.parentElement!==signals)signals.appendChild(chip);
      chip.style.display='inline-flex';
      chip.classList.add('dogson-signal-btn-v164');
      chip.dataset.dogsonQuick=type;
      if(!chip.dataset.v164Full)chip.dataset.v164Full=chip.textContent||'';
      const sl=shortLabel(type,chip.dataset.v164Full);
      if(chip.textContent!==sl)chip.textContent=sl;
      chip.setAttribute('role','button');chip.setAttribute('tabindex','0');chip.setAttribute('aria-haspopup','dialog');
    });
    if(badgeBox)badgeBox.hidden=true;

    const p=$('.portfolio-mini',card);
    if(p){
      if(p.parentElement!==actions)actions.appendChild(p);
      p.classList.add('dogson-portfolio-btn-v164');
      p.classList.remove('dogson-portfolio-action-v163');
      const held=p.classList.contains('held')||/已持有|已加入|✓/.test(p.textContent||'');
      const label=held?'✓ 庫存':'＋ 庫存';if(p.textContent!==label)p.textContent=label;
      p.setAttribute('aria-label',held?'編輯庫存':'加入庫存');
    }
  }

  function wireReasons(card){
    $$('.dogson-key-list span',card).forEach(x=>{x.dataset.dogsonQuick='reason';x.classList.add('dogson-key-btn-v164');x.setAttribute('role','button');x.setAttribute('tabindex','0');x.setAttribute('aria-haspopup','dialog')});
  }

  function card(card){card.classList.add('dogson-v164-card');actionStrip(card);wireReasons(card)}
  function run(){if(busy)return;busy=true;try{$$('#cards .card').forEach(card)}finally{busy=false}}
  function schedule(){if(busy)return;clearTimeout(timer);timer=setTimeout(run,60)}

  document.addEventListener('click',e=>{
    const chip=e.target.closest('[data-dogson-quick]');if(!chip)return;
    const card=chip.closest('.card');if(!card)return;
    e.preventDefault();e.stopImmediatePropagation();
    showSheet(card,chip.dataset.dogsonQuick,chip.dataset.v164Full||chip.textContent);
  },true);
  document.addEventListener('keydown',e=>{
    const chip=e.target.closest?.('[data-dogson-quick]');if(!chip||!['Enter',' '].includes(e.key))return;
    const card=chip.closest('.card');if(!card)return;
    e.preventDefault();e.stopImmediatePropagation();showSheet(card,chip.dataset.dogsonQuick,chip.dataset.v164Full||chip.textContent);
  },true);
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeSheet()});

  function start(){ensureSheet();run();const obs=new MutationObserver(schedule);if(document.body)obs.observe(document.body,{subtree:true,childList:true});setTimeout(run,220);setTimeout(run,800);setInterval(run,5000)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

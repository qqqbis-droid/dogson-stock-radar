(()=>{
  if(window.__DOGSON_UI_INTERACTIONS_V163__) return;
  window.__DOGSON_UI_INTERACTIONS_V163__=1;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/^[🟢🟡🔴🌱🔥⚠️🚫🚂✨⭐💼]+\s*/,'').replace(/\s+/g,' ').trim();
  let busy=false,timer=null,lastFocus=null;

  function stockTitle(card){
    const name=clean($('.name',card)?.childNodes?.[0]?.textContent||$('.name',card)?.textContent||'個股');
    const code=clean($('.code',card)?.textContent||'');
    return code?`${name} ${code}`:name;
  }

  function ensureSheet(){
    let back=$('#dogsonQuickDetailBack');
    if(back) return back;
    back=document.createElement('div');
    back.id='dogsonQuickDetailBack';
    back.className='dogson-quick-detail-back';
    back.hidden=true;
    back.innerHTML=`<section class="dogson-quick-detail" role="dialog" aria-modal="true" aria-labelledby="dogsonQuickDetailTitle">
      <div class="dogson-quick-detail-handle" aria-hidden="true"></div>
      <div class="dogson-quick-detail-top">
        <div><div class="dogson-quick-detail-kicker">快速查看</div><div id="dogsonQuickDetailTitle" class="dogson-quick-detail-title">詳細資料</div></div>
        <button type="button" class="dogson-quick-detail-close" aria-label="關閉">×</button>
      </div>
      <div class="dogson-quick-detail-body"></div>
    </section>`;
    document.body.appendChild(back);
    back.addEventListener('click',e=>{
      if(e.target===back||e.target.closest('.dogson-quick-detail-close')) closeSheet();
    });
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!back.hidden)closeSheet()});
    return back;
  }

  function closeSheet(){
    const back=$('#dogsonQuickDetailBack');
    if(!back||back.hidden)return;
    back.classList.remove('show');
    setTimeout(()=>{back.hidden=true;document.body.classList.remove('dogson-sheet-open');try{lastFocus?.focus()}catch{}},160);
  }

  function cloneSection(node){
    if(!node)return null;
    const c=node.cloneNode(true);
    c.removeAttribute('id');
    c.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));
    c.querySelectorAll('button,a,input,select,textarea').forEach(x=>{
      x.setAttribute('tabindex','-1');
      if(x.tagName==='BUTTON')x.disabled=true;
    });
    return c;
  }

  function qualityPanel(card){
    const wrap=document.createElement('div');
    wrap.className='dogson-quick-detail-stack';
    const intro=document.createElement('div');
    intro.className='dogson-quick-detail-intro';
    intro.textContent='這裡拆開目前的分數、動能與多時間框架；只用來理解為什麼被標成這個品質。';
    wrap.append(intro);
    const picks=[];
    ['.parts.intradayparts','.parts.closeparts','.parts.daytradeparts','.parts','.metrics','.mtfbox'].forEach(sel=>{
      const n=$(sel,card);if(n&&!picks.includes(n))picks.push(n);
    });
    picks.slice(0,3).forEach(n=>{const c=cloneSection(n);if(c)wrap.append(c)});
    return wrap;
  }

  function reasonPanel(card,label){
    const targetText=clean(label).replace(/^關鍵理由\s*/,'');
    const candidates=$$('.stagechip,.entrywhy span,.entrymeta span,.reason,.mtfcell,.metric,.part',card);
    const hit=candidates.find(x=>clean(x.textContent).includes(targetText)||targetText.includes(clean(x.textContent)));
    const owner=hit?.closest('.stagebox,.entrybox,.mtfbox,.daytradebox,.portfolio-decision,.portfoliobox');
    if(owner)return cloneSection(owner);
    const fallback=$('.entrybox',card)||$('.stagebox',card)||$('.mtfbox',card);
    const wrap=document.createElement('div');
    wrap.className='dogson-quick-detail-stack';
    const intro=document.createElement('div');
    intro.className='dogson-quick-detail-intro';
    intro.innerHTML=`你點的是「<b>${targetText||'關鍵條件'}</b>」。以下顯示最接近的判讀區塊。`;
    wrap.append(intro);
    const c=cloneSection(fallback);if(c)wrap.append(c);
    return wrap;
  }

  function detailSource(card,type,label){
    if(type==='stage') return cloneSection($('.stagebox',card));
    if(type==='entry') return cloneSection($('.entrybox',card));
    if(type==='quality') return qualityPanel(card);
    if(type==='portfolio') return cloneSection($('.portfolio-decision',card)||$('.portfoliobox',card));
    if(type==='reason') return reasonPanel(card,label);
    return cloneSection($('.entrybox',card)||$('.stagebox',card));
  }

  function openSheet(card,type,label,trigger){
    const back=ensureSheet(),body=$('.dogson-quick-detail-body',back),title=$('.dogson-quick-detail-title',back),kicker=$('.dogson-quick-detail-kicker',back);
    const source=detailSource(card,type,label);
    lastFocus=trigger||document.activeElement;
    title.textContent=`${stockTitle(card)}｜${clean(label)||'詳細資料'}`;
    kicker.textContent=type==='stage'?'生命週期詳細':type==='entry'?'進場判讀詳細':type==='quality'?'分數與動能詳細':type==='portfolio'?'庫存判讀詳細':'條件詳細';
    body.innerHTML='';
    if(source)body.append(source);else body.innerHTML='<div class="dogson-quick-detail-empty">目前沒有更多細節。</div>';
    back.hidden=false;
    document.body.classList.add('dogson-sheet-open');
    requestAnimationFrame(()=>back.classList.add('show'));
    setTimeout(()=>$('.dogson-quick-detail-close',back)?.focus(),40);
  }

  function makeClickable(el,type,card){
    if(!el||el.dataset.v163Click==='1')return;
    el.dataset.v163Click='1';
    el.classList.add('dogson-clickable-status');
    el.setAttribute('role','button');
    el.setAttribute('tabindex','0');
    el.setAttribute('aria-haspopup','dialog');
    const go=e=>{
      if(e.type==='keydown'&&!['Enter',' '].includes(e.key))return;
      if(e.type==='keydown')e.preventDefault();
      e.stopPropagation();
      openSheet(card,type,el.textContent,el);
    };
    el.addEventListener('click',go);
    el.addEventListener('keydown',go);
  }

  function movePortfolio(card){
    const btn=$('.portfolio-mini',card),score=$('.score',card),wrap=score?.parentElement;
    if(!btn||!wrap)return;
    wrap.classList.add('dogson-score-wrap-v163');
    btn.classList.add('dogson-portfolio-action-v163');
    if(btn.parentElement!==wrap)wrap.appendChild(btn);
    const held=btn.classList.contains('held')||/已持有|已加入/.test(btn.textContent||'');
    const label=held?'✓ 庫存':'＋ 庫存';
    if(btn.textContent!==label)btn.textContent=label;
    btn.setAttribute('aria-label',held?'編輯庫存':'加入庫存');
  }

  function wireCard(card){
    movePortfolio(card);
    const brief=$('.dogson-card-brief',card);
    if(brief){
      makeClickable($('.cat',brief),'stage',card);
      makeClickable($('.entrylight',brief),'entry',card);
      makeClickable($('.quality',brief),'quality',card);
      makeClickable($('.dogson-hold-pill',brief),'portfolio',card);
      makeClickable($('.dogson-reason-status',brief),'portfolio',card);
    }
    $$('.dogson-key-list span',card).forEach(x=>makeClickable(x,'reason',card));
  }

  function run(){
    if(busy)return;busy=true;
    try{$$('#cards .card').forEach(wireCard)}finally{busy=false}
  }
  function schedule(){if(busy)return;clearTimeout(timer);timer=setTimeout(run,70)}
  function start(){
    ensureSheet();run();
    const obs=new MutationObserver(schedule);
    if(document.body)obs.observe(document.body,{subtree:true,childList:true});
    setTimeout(run,250);setTimeout(run,900);setInterval(run,5000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

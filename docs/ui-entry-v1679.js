(()=>{
  if(window.__DOGSON_ENTRY_DETAIL_V1679__) return;
  window.__DOGSON_ENTRY_DETAIL_V1679__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/^[🟢🟡🔴✅⚠️⛔]+\s*/,'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uniq=a=>[...new Set(a.map(clean).filter(Boolean))];

  function stockTitle(card){
    const n=$('.name',card);let name='個股';
    if(n){const node=[...n.childNodes].find(x=>x.nodeType===Node.TEXT_NODE);name=clean(node?.textContent||n.textContent)}
    const code=clean($('.code',card)?.textContent||'');
    return code?`${name} ${code}`:name;
  }

  function ensureSheet(){
    let back=$('#dogsonEntryDetailBack');
    if(back)return back;
    back=document.createElement('div');
    back.id='dogsonEntryDetailBack';
    back.className='dogson-entry-detail-back';
    back.hidden=true;
    back.innerHTML=`<section class="dogson-entry-detail" role="dialog" aria-modal="true" aria-labelledby="dogsonEntryDetailTitle">
      <div class="dogson-entry-detail-handle" aria-hidden="true"></div>
      <div class="dogson-entry-detail-top"><div><div class="dogson-entry-detail-kicker">進場判讀詳細</div><div id="dogsonEntryDetailTitle" class="dogson-entry-detail-title">進場判讀</div></div><button type="button" class="dogson-entry-detail-close" aria-label="關閉">×</button></div>
      <div class="dogson-entry-detail-body"></div>
    </section>`;
    document.body.appendChild(back);
    back.addEventListener('click',e=>{if(e.target===back||e.target.closest('.dogson-entry-detail-close'))closeSheet()});
    return back;
  }

  function closeSheet(){
    const back=$('#dogsonEntryDetailBack');if(!back||back.hidden)return;
    back.classList.remove('show');
    setTimeout(()=>{back.hidden=true;document.body.classList.remove('dogson-entry-sheet-open')},150);
  }

  function topic(s){
    s=clean(s);
    if(/相對強弱/.test(s))return'relative';
    if(/多時框|多框|三框|60K|60分|20T|60T|日K/.test(s))return'mtf';
    if(/VWAP/.test(s))return'vwap';
    if(/量價|量速|動能/.test(s))return'flow';
    if(/族群/.test(s))return'sector';
    if(/流動性|追價/.test(s))return'liquidity';
    if(/結構|5分K|價格結構/.test(s))return'structure';
    if(/區間位置/.test(s))return'position';
    if(/生命週期|Stage/.test(s))return'stage';
    return'misc:'+s;
  }

  function entryData(card,chip){
    const box=$('.entrybox',card);
    const src=$('.entrylight',box)||chip;
    let key='yellow';
    if(src?.classList.contains('green'))key='green';
    if(src?.classList.contains('red'))key='red';
    if(src?.classList.contains('yellow'))key='yellow';
    const label=clean(chip?.dataset?.v164Full||src?.textContent||chip?.textContent||'等確認').replace(/^動能\s*[：:]\s*/,'');
    const headline=clean($('.entryheadline',box)?.textContent||'');
    const good=uniq($$('.entrywhy span:not(.wait):not(.block)',box).map(x=>x.textContent));
    const wait=uniq($$('.entrywhy span.wait',box).map(x=>x.textContent));
    const block=uniq($$('.entrywhy span.block',box).map(x=>x.textContent));
    const unresolved=new Set([...wait,...block].map(topic));
    const established=good.filter(x=>{const t=topic(x);return t.startsWith('misc:')||!unresolved.has(t)}).slice(0,5);
    const meta=uniq($$('.entrymeta span',box).map(x=>x.textContent));
    const market=meta.find(x=>/^大盤\s/.test(x))||'';
    return{key,label,headline,wait:wait.slice(0,5),block:block.slice(0,5),established,meta,market};
  }

  function stage(card){
    const c=$('.dogson-action-strip-v164 .cat',card)||$('.dogson-card-details .cat',card)||$('.cat',card);
    return clean(c?.dataset?.v164Full||c?.textContent||'');
  }

  function riskText(card,d){
    if(d.block.length)return d.block.slice(0,2).join('；');
    const s=stage(card);
    if(/回踩|承接/.test(s))return'跌破 VWAP／短線關鍵支撐，而且反抽站不回 → 暫停進場。';
    if(/剛啟動/.test(s))return'跌回突破區且無法站回 → 取消追價，等待重新整理。';
    if(/蓄勢/.test(s))return'支撐失守或相對市場明顯轉弱 → 暫停這一輪進場觀察。';
    if(/趨勢|持有/.test(s))return'短線結構破壞且反抽失敗 → 不新增部位，重新評估。';
    if(/轉弱|失效/.test(s))return'未重新站回關鍵結構前，不把反彈視為新進場訊號。';
    return'跌破 VWAP／短線關鍵結構且反抽站不回 → 暫停進場。';
  }

  function cloneTech(card){
    const wrap=document.createElement('div');wrap.className='dogson-entry-tech-body';
    const meta=$$('.entrymeta span',$('.entrybox',card)).map(x=>clean(x.textContent)).filter(Boolean);
    if(meta.length){const chips=document.createElement('div');chips.className='dogson-entry-tech-chips';chips.innerHTML=meta.map(x=>`<span>${esc(x)}</span>`).join('');wrap.append(chips)}
    const mtf=$('.mtfbox',card);
    if(mtf){const c=mtf.cloneNode(true);c.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));wrap.append(c)}
    if(!wrap.children.length){const e=document.createElement('div');e.className='dogson-entry-detail-empty';e.textContent='目前沒有更多技術細節。';wrap.append(e)}
    return wrap;
  }

  function listSection(title,items,kind,empty=''){
    if(!items.length&&!empty)return'';
    const rows=items.length?items.map(x=>`<div class="dogson-entry-row"><span>${kind==='good'?'✓':kind==='bad'?'!':'○'}</span><div>${esc(x)}</div></div>`).join(''):`<div class="dogson-entry-row dogson-entry-row-empty"><span>○</span><div>${esc(empty)}</div></div>`;
    return `<section class="dogson-entry-section dogson-entry-${kind}"><div class="dogson-entry-section-title">${esc(title)}</div>${rows}</section>`;
  }

  function render(card,chip){
    const d=entryData(card,chip),back=ensureSheet(),body=$('.dogson-entry-detail-body',back),title=$('.dogson-entry-detail-title',back);
    title.textContent=`${stockTitle(card)}｜${d.label}`;
    const count=d.key==='red'?d.block.length:d.wait.length;
    const statusText=d.key==='green'?`${d.label}`:d.key==='red'?`${d.label}${count?` · ${count} 個阻擋`:''}`:`${d.label}${count?` · 還差 ${count} 項`:''}`;
    const statusIcon=d.key==='green'?'🟢':d.key==='red'?'🔴':'🟡';
    const decision=d.headline|| (d.key==='green'?'條件同步，可列入小量試單觀察。':d.key==='red'?'目前有阻擋條件，先不進。':'方向未壞，但買點條件還沒完全到位。');
    let html=`<section class="dogson-entry-hero dogson-entry-hero-${d.key}"><div class="dogson-entry-hero-label">現在能不能進</div><div class="dogson-entry-hero-status">${statusIcon} ${esc(statusText)}</div><div class="dogson-entry-hero-head">${esc(decision)}</div>${d.market?`<div class="dogson-entry-market">環境：${esc(d.market.replace(/^大盤\s*/,''))}</div>`:''}</section>`;
    if(d.key==='red')html+=listSection('目前阻擋',d.block,'bad',d.headline||'目前條件不足，先不進。');
    else if(d.key==='yellow')html+=listSection('還差什麼',d.wait,'wait','等待回踩或關鍵條件補齊。');
    else if(d.wait.length)html+=listSection('仍可留意',d.wait,'wait');
    html+=listSection('已經成立',d.established,'good');
    html+=`<section class="dogson-entry-section dogson-entry-alert"><div class="dogson-entry-section-title">失效警戒</div><div class="dogson-entry-alert-text">${esc(riskText(card,d))}</div></section>`;
    html+=`<details class="dogson-entry-tech"><summary>查看技術細節</summary><div class="dogson-entry-tech-slot"></div></details>`;
    body.innerHTML=html;
    $('.dogson-entry-tech-slot',body)?.append(cloneTech(card));
    back.hidden=false;document.body.classList.add('dogson-entry-sheet-open');requestAnimationFrame(()=>back.classList.add('show'));
  }

  window.addEventListener('click',e=>{
    const chip=e.target.closest?.('[data-dogson-quick="entry"]');if(!chip)return;
    const card=chip.closest('.card');if(!card)return;
    e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();render(card,chip);
  },true);
  window.addEventListener('keydown',e=>{
    if(e.key==='Escape'){closeSheet();return}
    if(!['Enter',' '].includes(e.key))return;
    const chip=e.target.closest?.('[data-dogson-quick="entry"]');if(!chip)return;
    const card=chip.closest('.card');if(!card)return;
    e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();render(card,chip);
  },true);
})();

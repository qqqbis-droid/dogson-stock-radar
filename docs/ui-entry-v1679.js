(()=>{
  if(window.__DOGSON_ENTRY_DETAIL_V1680__) return;
  window.__DOGSON_ENTRY_DETAIL_V1680__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/^[🟢🟡🔴✅⚠️⛔]+\s*/,'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uniq=a=>[...new Set(a.map(clean).filter(Boolean))];

  function marketContext(mkt){
    const mode=String(mkt?.market_mode||'—');
    const raw=Number(mkt?.market_score);
    const score=Number.isFinite(raw)?raw:0;
    const scoreKnown=score>0;
    const defensive=mode==='防守'||/偏弱|防守/.test(mode)||(scoreKnown&&score<6);
    const systemic=/極弱|失效|空頭|系統性|全面防守|高風險/.test(mode)||(scoreKnown&&score<=2);
    const scoreText=scoreKnown?` ${score.toFixed(1).replace(/\.0$/,'')}/15`:'';
    return{
      mode,score,defensive,systemic,
      label:`大盤 ${mode}${scoreText}`,
      advisory:defensive&&!systemic?`大盤 ${mode}${scoreText}｜個股條件可成立，但第一筆部位宜縮小，避免追價；優先等回踩承接。`:'',
      brake:systemic?`大盤 ${mode}${scoreText} 已達系統性風險煞車門檻，暫緩新倉。`:''
    };
  }

  // Market is a risk regulator, not a normal entry requirement.
  // Keep the original 100-point stock score and original entry rules intact;
  // only remove ordinary weak-market vetoes. A true systemic-risk state may still brake new entries.
  if(typeof entryDecision==='function'&&!window.__DOGSON_MARKET_ADVISORY_V1680__){
    window.__DOGSON_MARKET_ADVISORY_V1680__=1;
    const baseEntryDecision=entryDecision;
    entryDecision=function(r,mkt){
      let actual=mkt;
      if(actual===undefined){try{actual=typeof market!=='undefined'?market:undefined}catch{}}
      const mc=marketContext(actual);
      const neutral={...(actual||{}),market_mode:'中性',market_score:8};
      const stockDecision=baseEntryDecision(r,neutral);

      if(mc.systemic){
        const block=uniq([...(stockDecision.block||[]),mc.brake]);
        return{
          ...stockDecision,
          key:'red',icon:'🔴',label:'先不進',
          headline:'個股條件之外，大盤已觸發系統性風險煞車',
          wait:[],block,
          marketMode:mc.mode,marketScore:mc.score,
          marketBrake:true,marketAdvisory:''
        };
      }

      const out={
        ...stockDecision,
        marketMode:mc.mode,marketScore:mc.score,
        marketBrake:false,marketAdvisory:mc.advisory
      };
      if(mc.defensive&&stockDecision.key==='green'){
        out.headline='個股條件成立；大盤偏弱，第一筆部位縮小';
      }
      return out;
    };
  }

  function currentMarketContext(){
    let m;
    try{m=typeof market!=='undefined'?market:undefined}catch{}
    return marketContext(m);
  }

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
    if(/^大盤\s|環境門檻|系統性風險/.test(s))return'market';
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
    const wait=uniq($$('.entrywhy span.wait',box).map(x=>x.textContent)).filter(x=>topic(x)!=='market');
    const block=uniq($$('.entrywhy span.block',box).map(x=>x.textContent));
    const unresolved=new Set([...wait,...block].map(topic));
    const established=good.filter(x=>{const t=topic(x);return t.startsWith('misc:')||!unresolved.has(t)}).slice(0,5);
    const meta=uniq($$('.entrymeta span',box).map(x=>x.textContent));
    const mc=currentMarketContext();
    return{key,label,headline,wait:wait.slice(0,5),block:block.slice(0,5),established,meta,market:mc};
  }

  function stage(card){
    const c=$('.dogson-action-strip-v164 .cat',card)||$('.dogson-card-details .cat',card)||$('.cat',card);
    return clean(c?.dataset?.v164Full||c?.textContent||'');
  }

  function riskText(card,d){
    const nonMarket=d.block.filter(x=>topic(x)!=='market');
    if(nonMarket.length)return nonMarket.slice(0,2).join('；');
    if(d.market.systemic)return d.market.brake;
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

  function marketSection(mc){
    if(mc.systemic)return'';
    if(!mc.advisory)return'';
    return `<section class="dogson-entry-section dogson-entry-market-advisory"><div class="dogson-entry-section-title">⚠️ 市場環境提醒</div><div class="dogson-entry-market-advisory-text">${esc(mc.advisory)}</div><div class="dogson-entry-market-advisory-note">大盤只調節部位與進場保守度，不列入一般「還差什麼」。</div></section>`;
  }

  function renderSheet(card,chip){
    const d=entryData(card,chip),back=ensureSheet(),body=$('.dogson-entry-detail-body',back),title=$('.dogson-entry-detail-title',back);
    title.textContent=`${stockTitle(card)}｜${d.label}`;
    const count=d.key==='red'?d.block.filter(x=>topic(x)!=='market').length:d.wait.length;
    const statusText=d.key==='green'?`${d.label}`:d.key==='red'?`${d.label}${count?` · ${count} 個阻擋`:''}`:`${d.label}${count?` · 還差 ${count} 項`:''}`;
    const statusIcon=d.key==='green'?'🟢':d.key==='red'?'🔴':'🟡';
    const decision=d.headline|| (d.key==='green'?'條件同步，可列入小量試單觀察。':d.key==='red'?'目前有阻擋條件，先不進。':'方向未壞，但買點條件還沒完全到位。');
    let html=`<section class="dogson-entry-hero dogson-entry-hero-${d.key}"><div class="dogson-entry-hero-label">現在能不能進</div><div class="dogson-entry-hero-status">${statusIcon} ${esc(statusText)}</div><div class="dogson-entry-hero-head">${esc(decision)}</div></section>`;
    html+=marketSection(d.market);
    if(d.key==='red')html+=listSection(d.market.systemic?'目前煞車':'目前阻擋',d.block,'bad',d.headline||'目前條件不足，先不進。');
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
    e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();renderSheet(card,chip);
  },true);
  window.addEventListener('keydown',e=>{
    if(e.key==='Escape'){closeSheet();return}
    if(!['Enter',' '].includes(e.key))return;
    const chip=e.target.closest?.('[data-dogson-quick="entry"]');if(!chip)return;
    const card=chip.closest('.card');if(!card)return;
    e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();renderSheet(card,chip);
  },true);

  // Re-render once so the main-card entry light and summary counts adopt the adjusted market policy immediately.
  setTimeout(()=>{try{if(typeof window.render==='function')window.render()}catch{}},80);
})();

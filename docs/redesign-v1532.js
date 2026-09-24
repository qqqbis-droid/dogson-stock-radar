(()=>{
  if(window.__DOGSON_LIGHT_REDESIGN_V1532__) return;
  window.__DOGSON_LIGHT_REDESIGN_V1532__ = true;

  const TEXT_RULES = [
    [/([①-⑳]\s*)?Step\s*\d+\s*[｜|]\s*/g, ''],
    [/Step\s*\d+/g, ''],
    [/Stage 2\.0/g, '階段判讀'],
    [/\bStage\b/g, '階段'],
    [/\bOutcome\b/g, '結果'],
    [/\bcomponent(s)?\b/gi, '項目'],
    [/\bhorizon\b/gi, '期間'],
    [/Free Edition v[\d.]+｜原始構想補完版/g, '波段決策雷達｜簡潔版'],
    [/⚡\s*盤中波段/g, '⚡ 找波段'],
    [/🎯\s*當沖模式/g, '🎯 當沖'],
    [/🌙\s*盤後波段/g, '🌙 盤後'],
    [/盤中進場三燈/g, '現在能不能進？'],
    [/多時間框架：5分＋60分＋日K要互相確認/g, '多時間框架'],
    [/歷史驗證：讓分數接受真實結果檢驗/g, '歷史表現'],
    [/獨立當沖模式：只回答今天這一筆好不好做/g, '當沖判斷'],
    [/高品質二次篩選/g, '只看高品質'],
    [/今日新進蓄勢/g, '今天進入蓄勢'],
    [/今日新進剛啟動/g, '今天剛啟動'],
    [/一路改善/g, '持續轉強'],
    [/庫存今日轉弱/g, '庫存轉弱'],
    [/今日轉過熱/g, '今天過熱'],
    [/今日族群加速/g, '族群加速'],
    [/近即時報價準備中｜技術結構仍採5分K/g, '行情更新中｜技術結構採 5 分K'],
    [/讀取大盤環境…/g, '正在更新大盤…'],
    [/正在讀取最新資料…/g, '正在更新資料…'],
    [/讀取中/g, '更新中'],
    [/掃描/g, '更新'],
    [/查看完整/g, '查看詳情'],
    [/完整分析/g, '詳細分析'],
    [/更多數據/g, '詳細數據']
  ];

  function cleanString(input){
    let out=String(input??'');
    for(const [rx,to] of TEXT_RULES) out=out.replace(rx,to);
    return out.replace(/\s*｜\s*｜\s*/g,'｜').replace(/^\s*｜\s*/,'').replace(/\s{2,}/g,' ');
  }

  function simplifyText(root=document.body){
    if(!root) return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){
      const p=node.parentElement;
      if(!p||['SCRIPT','STYLE','NOSCRIPT','TEXTAREA'].includes(p.tagName)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }});
    const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node=>{const next=cleanString(node.nodeValue);if(next!==node.nodeValue)node.nodeValue=next});
    document.querySelectorAll('input[placeholder]').forEach(el=>{
      const p=el.getAttribute('placeholder')||'';
      if(p.includes('輸入股票代號或名稱')) el.setAttribute('placeholder','搜尋股票代號或名稱');
    });
    const sub=document.querySelector('header .sub'); if(sub) sub.textContent='波段決策雷達｜簡潔版';
    const footer=document.getElementById('footerText'); if(footer) footer.textContent='分數看條件是否同步，不代表上漲機率｜大盤環境分獨立';
  }

  function ensureMoreMarket(){
    const wrap=document.querySelector('.wrap');
    const cards=document.getElementById('cards');
    if(!wrap||!cards) return;
    let more=document.getElementById('dogsonMoreMarket');
    if(!more){
      more=document.createElement('details');
      more.id='dogsonMoreMarket';
      more.className='dogson-more-market';
      more.innerHTML='<summary>更多市場資訊</summary><div class="dogson-more-market-body"></div>';
      cards.insertAdjacentElement('afterend',more);
    }
    const body=more.querySelector('.dogson-more-market-body');
    ['rotationbox','validationbox'].forEach(id=>{
      const el=document.getElementById(id);if(el&&el.parentElement!==body)body.appendChild(el);
    });
  }

  function rearrangePage(){
    const wrap=document.querySelector('.wrap'); if(!wrap) return;
    const selectors=['header','.tabs','.controls','#marketbox','#changebox','#entrySummary','#liveStatus','.meta','#portfolioSummary','#cards'];
    let anchor=null;
    selectors.forEach(sel=>{
      const el=wrap.querySelector(sel); if(!el) return;
      if(!anchor){ if(el!==wrap.firstElementChild) wrap.insertBefore(el,wrap.firstElementChild); }
      else if(anchor.nextElementSibling!==el) anchor.insertAdjacentElement('afterend',el);
      anchor=el;
    });
    ensureMoreMarket();
  }

  function conciseReason(text){
    const s=cleanString(text).trim();
    if(!s) return '';
    const first=s.split(/[。；;]/)[0].trim();
    return first.length>58?first.slice(0,58)+'…':first;
  }

  function compactCard(card){
    if(!card||card.dataset.redesignCompact==='1') return;
    card.dataset.redesignCompact='1';
    const top=card.querySelector('.top');
    if(!top) return;
    const entry=card.querySelector('.entrybox');
    const stage=card.querySelector('.stagebox');
    const entryLight=entry?.querySelector('.entrylight');
    const entryHeadline=entry?.querySelector('.entryheadline')?.textContent;
    const stageReason=stage?.querySelector('.stagereason')?.textContent;
    const category=card.querySelector('.cat');
    const quality=card.querySelector('.quality');
    const brief=document.createElement('div');
    brief.className='dogson-card-brief';
    const badges=[];
    if(category) badges.push(category.outerHTML);
    if(entryLight) badges.push(entryLight.outerHTML);
    if(quality) badges.push(quality.outerHTML);
    const headline=conciseReason(entryHeadline||stageReason||'點開查看完整分析');
    brief.innerHTML=`<div class="dogson-card-badges">${badges.join('')}</div><div class="dogson-card-headline">${headline}</div>`;
    top.insertAdjacentElement('afterend',brief);
    if(category) category.style.display='none';
    if(quality) quality.style.display='none';
    const detail=document.createElement('details');
    detail.className='dogson-card-details';
    detail.innerHTML='<summary>查看詳細分析</summary><div class="dogson-card-details-body"></div>';
    const body=detail.querySelector('.dogson-card-details-body');
    const keep=new Set([top,brief]);
    [...card.children].forEach(child=>{
      if(keep.has(child)||child===detail) return;
      body.appendChild(child);
    });
    card.appendChild(detail);
  }

  function compactCards(){ document.querySelectorAll('#cards .card').forEach(compactCard); }

  function renameSectionTitles(){
    const mappings=[
      ['.changetitle','今天值得注意'],
      ['.entrysummarytitle','現在能不能進？'],
      ['.rotationtitle','族群資金'],
      ['.validationtitle','歷史表現']
    ];
    mappings.forEach(([sel,text])=>document.querySelectorAll(sel).forEach(el=>{if(el.textContent.trim())el.textContent=text}));
    document.querySelectorAll('.guide-title').forEach(el=>{el.textContent=cleanString(el.textContent).replace(/^[①-⑳]\s*/,'').trim()});
    document.querySelectorAll('.guide-tip,.guide-line,.entrynote,.changesub,.validationnote,.mtfnote,.stagehint,.daytradesource').forEach(el=>{
      const t=cleanString(el.textContent).trim(); if(t.length>120) el.classList.add('dogson-long-copy');
    });
  }

  function simplifyFilterCopy(){
    document.querySelectorAll('.decision-filterbtn').forEach(btn=>{
      let t=btn.textContent.trim();
      t=t.replace('✨ 綠燈＋高品質黃','精選機會').replace(/✨\s*只看高品質\s*(ON|OFF)?/,'只看高品質').replace('清除事件篩選','清除篩選');
      btn.textContent=t;
    });
    document.querySelectorAll('.decision-filter-note').forEach(el=>{
      el.textContent=el.textContent.includes('預設')?'預設只顯示較值得看的機會；需要時可切換全部。':'點上方條件即可篩選，再點一次取消。';
    });
  }

  function apply(){
    document.documentElement.classList.add('dogson-light-v1532');
    rearrangePage(); simplifyText(); renameSectionTitles(); compactCards(); simplifyFilterCopy();
  }

  let timer=null;
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(apply,40)};
  const observer=new MutationObserver(schedule);
  if(document.body) observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',apply,{once:true}); else apply();
  setTimeout(apply,250);
})();

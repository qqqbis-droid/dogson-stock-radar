(function(){
  const STYLE_ID='supportResistanceClassicStyle';

  function ensureStyle(){
    if(document.getElementById(STYLE_ID))return;
    const s=document.createElement('style');
    s.id=STYLE_ID;
    s.textContent=`
.sr-classic-block{margin-top:12px}
.sr-classic-block>h3{margin-bottom:8px}
.srbox.sr-classic{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px}
.srbox.sr-classic .sr{border:1px solid var(--line);border-radius:14px;padding:11px 10px;background:var(--card);min-width:0}
.srbox.sr-classic .sr.support{box-shadow:inset 3px 0 0 var(--green)}
.srbox.sr-classic .sr.resistance{box-shadow:inset 3px 0 0 var(--red)}
.srbox.sr-classic .srtitle{font-size:.78rem;font-weight:850;line-height:1.35;margin-bottom:8px}
.srbox.sr-classic .srlevel{padding:8px 0;border-top:1px dashed var(--line)}
.srbox.sr-classic .srlevel:first-of-type{border-top:0;padding-top:0}
.srbox.sr-classic .srlevel:last-of-type{padding-bottom:0}
.srbox.sr-classic .srlevel-head{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:3px}
.srbox.sr-classic .srlevel-name{font-size:.66rem;font-weight:800;color:var(--muted);min-width:0}
.srbox.sr-classic .srlevel-distance{font-size:.62rem;font-weight:750;color:var(--muted);text-align:right;white-space:nowrap}
.srbox.sr-classic .srprice{font-size:1.12rem;font-weight:900;line-height:1.2;letter-spacing:-.01em;overflow-wrap:anywhere}
.srbox.sr-classic .srbasis{font-size:.67rem;line-height:1.4;color:var(--muted);margin-top:5px}
.srbox.sr-classic .srstrength{font-size:.62rem;line-height:1.35;color:var(--muted);margin-top:4px}
.srbox.sr-classic .srstate{display:inline-block;font-size:.58rem;padding:2px 6px;border-radius:999px;background:var(--soft);color:var(--muted);margin-top:5px}
.srbox.sr-classic .sr-empty{font-size:.67rem;color:var(--muted);line-height:1.45;padding:4px 0}
.sr-classic-rules{margin-top:8px;border-top:1px dashed var(--line);padding-top:7px}
.sr-classic-rules summary{cursor:pointer;font-size:.65rem;font-weight:750;color:var(--muted);list-style:none}
.sr-classic-rules summary::-webkit-details-marker{display:none}
.sr-classic-rules summary:after{content:'＋';float:right}
.sr-classic-rules[open] summary:after{content:'－'}
.sr-classic-rule-body{font-size:.62rem;line-height:1.45;color:var(--muted);margin-top:6px}
.sr-classic-note{font-size:.66rem;color:var(--muted);line-height:1.45;margin-top:8px}
@media(max-width:360px){.srbox.sr-classic{gap:7px}.srbox.sr-classic .sr{padding:9px 8px}.srbox.sr-classic .srprice{font-size:1.02rem}}
`;
    document.head.appendChild(s);
  }

  function text(el,sel){return el?.querySelector(sel)?.textContent?.trim()||''}
  function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}

  function distance(card){
    const raw=text(card,'.sr2-distance').replace(/\s+/g,' ');
    return raw.replace(/^距現價\s*/,'').trim();
  }
  function priceBand(card){
    const band=text(card,'.sr2-band').replace(/^價格帶\s*/, '').trim();
    return band||text(card,'.sr2-price')||'—';
  }
  function rankLabel(card,fallback){
    const raw=text(card,'.sr2-name');
    const m=raw.match(/\b([SR][12])\b/);
    return m?m[1]:fallback;
  }
  function levelHtml(card,fallback){
    if(!card)return'';
    const rank=rankLabel(card,fallback),dist=distance(card),basis=text(card,'.sr2-evidence')||'結構來源待補',strength=text(card,'.sr2-strength'),state=text(card,'.sr2-state'),rule=card.querySelector('.sr2-rule')?.innerHTML||'';
    return `<div class="srlevel"><div class="srlevel-head"><span class="srlevel-name">${esc(rank)}</span><span class="srlevel-distance">${esc(dist)}</span></div><div class="srprice">${esc(priceBand(card))}</div><div class="srbasis">${esc(basis)}</div>${strength?`<div class="srstrength">${esc(strength)}</div>`:''}${state?`<span class="srstate">${esc(state)}</span>`:''}${rule?`<details class="sr-classic-rules"><summary>確認／失效規則</summary><div class="sr-classic-rule-body">${rule}</div></details>`:''}</div>`;
  }
  function sideHtml(kind,cards){
    const support=kind==='support',icon=support?'🟢':'🔴',title=support?'支撐區':'壓力區',prefix=support?'S':'R';
    const body=cards.length?cards.map((c,i)=>levelHtml(c,`${prefix}${i+1}`)).join(''):`<div class="sr-empty">沒有可信${title}時不猜單一價位。</div>`;
    return `<div class="sr ${kind}"><div class="srtitle">${icon} ${title}</div>${body}</div>`;
  }

  function directLevelHtml(card,fallback){
    const rank=text(card,'.isd-zone-head span')||fallback;
    const label=text(card,'.isd-zone-head b');
    const price=text(card,'.isd-zone-price')||'—';
    const raw=[...card.querySelectorAll('small')].map(x=>x.textContent.trim()).join('｜');
    const parts=raw.split('｜').map(x=>x.trim()).filter(Boolean);
    const dist=(parts.find(x=>/^距離/.test(x))||'').replace(/^距離\s*/,'');
    const strength=parts.find(x=>/^強度/.test(x))||'';
    const basis=parts.filter(x=>!/^距離/.test(x)&&!/^強度/.test(x)).join('＋')||'結構來源待補';
    const title=label&&label!==rank?`${rank} · ${label}`:rank;
    return `<div class="srlevel"><div class="srlevel-head"><span class="srlevel-name">${esc(title)}</span><span class="srlevel-distance">${esc(dist)}</span></div><div class="srprice">${esc(price)}</div><div class="srbasis">${esc(basis)}</div>${strength?`<div class="srstrength">${esc(strength)}</div>`:''}</div>`;
  }
  function directSideHtml(kind,cards){
    const support=kind==='support',icon=support?'🟢':'🔴',title=support?'支撐區':'壓力區',prefix=support?'S':'R';
    const body=cards.length?cards.map((c,i)=>directLevelHtml(c,`${prefix}${i+1}`)).join(''):`<div class="sr-empty">沒有可信${title}時不猜單一價位。</div>`;
    return `<div class="sr ${kind}"><div class="srtitle">${icon} ${title}</div>${body}</div>`;
  }

  function restoreDirect(body){
    const sections=[...body.querySelectorAll(':scope > .isd-section')];
    const section=sections.find(s=>/支撐\s*[\/／|]\s*壓力/.test(s.querySelector(':scope > h3')?.textContent||''));
    if(!section)return false;
    if(section.classList.contains('sr-classic-block'))return true;
    const supports=[...section.querySelectorAll('.isd-zone.support')];
    const resistances=[...section.querySelectorAll('.isd-zone.resistance')];
    section.classList.add('sr-classic-block','sr-classic-direct');
    section.innerHTML=`<h3>支撐／壓力</h3><div class="srbox sr-classic">${directSideHtml('support',supports)}${directSideHtml('resistance',resistances)}</div><div class="sr-classic-note">以價格區間＋主要依據為主；S1/S2、R1/R2 仍由新版 S/R 2.0 Engine 重排。</div>`;
    return true;
  }

  function restoreSr2(body){
    const blocks=[...body.querySelectorAll(':scope > .detail-block')];
    const supportBlock=blocks.find(b=>/支撐區/.test(b.querySelector(':scope > h3')?.textContent||''));
    const resistanceBlock=blocks.find(b=>/壓力區/.test(b.querySelector(':scope > h3')?.textContent||''));
    if(!supportBlock&&!resistanceBlock)return false;
    const supports=[...(supportBlock?.querySelectorAll('.sr2-card.support')||[])];
    const resistances=[...(resistanceBlock?.querySelectorAll('.sr2-card.resistance')||[])];
    const wrap=document.createElement('div');
    wrap.className='detail-block sr-classic-block';
    wrap.innerHTML=`<h3>支撐／壓力</h3><div class="srbox sr-classic">${sideHtml('support',supports)}${sideHtml('resistance',resistances)}</div><div class="sr-classic-note">以價格區間＋主要依據為主；S1/S2、R1/R2 仍由新版 S/R 2.0 Engine 重排，不把單一中心價當成假精準價位。</div>`;
    const anchor=supportBlock||resistanceBlock;
    anchor.parentNode.insertBefore(wrap,anchor);
    supportBlock?.remove();
    resistanceBlock?.remove();
    return true;
  }

  function restore(){
    ensureStyle();
    const body=document.getElementById('detailBody');
    if(!body)return;
    if(restoreDirect(body))return;
    if(body.querySelector('.sr-classic-block'))return;
    restoreSr2(body);
  }

  document.addEventListener('radar:detail-rendered',()=>requestAnimationFrame(restore));
  document.addEventListener('radar:detail-core-rendered',()=>requestAnimationFrame(restore));
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensureStyle);else ensureStyle();
})();
(()=>{
'use strict';
const STYLE_ID='inukoPriceMapLiteStyle';
const MAP_CLASS='inuko-price-map';
const labels={R2:'延伸突破帶',R1:'第一突破帶',S1:'第一防守帶',S2:'深層防守帶'};
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function style(){if(document.getElementById(STYLE_ID))return;const s=document.createElement('style');s.id=STYLE_ID;s.textContent=`
.${MAP_CLASS}{margin:0 0 15px}.pm-head{padding:13px 14px;border-radius:16px;background:linear-gradient(135deg,#203d35,#315749);color:#fff}.pm-head small{display:block;font-size:.61rem;letter-spacing:.14em;opacity:.72;font-weight:850}.pm-head h3{margin:3px 0!important;color:#fff!important;font-size:1rem!important}.pm-head p{margin:0;font-size:.69rem;line-height:1.45;opacity:.82}.pm-lane{position:relative;display:grid;gap:9px;margin-top:10px;padding-left:17px}.pm-lane:before{content:'';position:absolute;left:5px;top:8px;bottom:8px;width:2px;background:var(--line);border-radius:2px}.pm-lane-label{font-size:.68rem;font-weight:900;letter-spacing:.035em}.pm-lane.break .pm-lane-label{color:#9a642f}.pm-lane.defend .pm-lane-label{color:#326a59}.pm-card{position:relative;border-radius:15px;padding:12px 13px;background:var(--card);border:1px solid var(--line)}.pm-card:before{content:'';position:absolute;left:-18px;top:25px;width:11px;height:11px;border-radius:50%;border:2px solid var(--card);box-shadow:0 0 0 1px var(--line)}.pm-lane.break .pm-card{border-color:rgba(176,111,49,.25);background:linear-gradient(135deg,rgba(201,145,78,.09),var(--card))}.pm-lane.break .pm-card:before{background:#bd7b3f}.pm-lane.defend .pm-card{border-color:rgba(53,112,92,.25);background:linear-gradient(135deg,rgba(72,133,111,.09),var(--card))}.pm-lane.defend .pm-card:before{background:#3f7e69}.pm-card-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.pm-card-title{display:flex;align-items:center;gap:6px;min-width:0;font-size:.78rem;font-weight:900}.pm-rank{display:inline-flex;align-items:center;justify-content:center;min-width:31px;height:23px;padding:0 6px;border-radius:7px;background:rgba(255,255,255,.76);border:1px solid rgba(80,95,87,.13);font-size:.65rem;font-weight:900}.pm-state{padding:4px 8px;border-radius:999px;background:var(--soft);color:var(--muted);font-size:.61rem;white-space:nowrap}.pm-price-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:end;margin-top:9px}.pm-center{font-size:1.43rem;font-weight:950;line-height:1.05;letter-spacing:-.025em}.pm-band{margin-top:4px;color:var(--muted);font-size:.69rem}.pm-distance{text-align:right;font-size:.66rem;font-weight:850;line-height:1.18}.pm-distance b{display:block;margin-top:2px;font-size:.83rem;color:var(--ink)}.pm-evidence{margin-top:9px;font-size:.72rem;line-height:1.45}.pm-stars{margin-top:7px;color:var(--muted);font-size:.7rem;letter-spacing:.02em}.pm-rule{margin-top:9px;padding-top:8px;border-top:1px dashed var(--line);font-size:.67rem;line-height:1.5;color:var(--muted)}.pm-rule p{margin:3px 0}.pm-rule b{color:var(--muted)}.pm-now{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;align-items:center;margin:11px 0 4px;padding:10px 12px;border-radius:13px;background:#253f36;color:#fff}.pm-now b{font-size:.9rem}.pm-now span{grid-row:1/3;display:inline-flex;align-items:center;justify-content:center;height:29px;min-width:47px;padding:0 8px;border-radius:8px;background:rgba(255,255,255,.12);font-size:.62rem;font-weight:900;letter-spacing:.08em}.pm-now small{font-size:.66rem;opacity:.78}.pm-empty{padding:10px 11px;border:1px dashed var(--line);border-radius:11px;background:var(--soft);color:var(--muted);font-size:.68rem}.pm-foot{margin-top:9px;padding:8px 10px;border-radius:10px;background:var(--soft);font-size:.66rem;line-height:1.5;color:var(--muted)}
.${MAP_CLASS} .sr2-card{position:relative;border-radius:15px!important;border-left:0!important}.pm-lane .sr2-card:before{content:'';position:absolute;left:-18px;top:25px;width:11px;height:11px;border-radius:50%;border:2px solid var(--card);box-shadow:0 0 0 1px var(--line)}.pm-lane.break .sr2-card{border:1px solid rgba(176,111,49,.25)!important;background:linear-gradient(135deg,rgba(201,145,78,.09),var(--card))!important}.pm-lane.break .sr2-card:before{background:#bd7b3f}.pm-lane.defend .sr2-card{border:1px solid rgba(53,112,92,.25)!important;background:linear-gradient(135deg,rgba(72,133,111,.09),var(--card))!important}.pm-lane.defend .sr2-card:before{background:#3f7e69}
`;document.head.appendChild(s)}
function rankFromSr2(card){const t=card?.querySelector('.sr2-name')?.textContent||'';return (t.match(/\b([SR][12])\b/)||[])[1]||''}
function relabelSr2(card){const r=rankFromSr2(card);if(!r)return;const name=card.querySelector('.sr2-name');if(name)name.innerHTML=`<span class="pm-rank">${r}</span><span>${labels[r]||r}</span>`}
function current(body){
  for(const tile of body.querySelectorAll('.isd-grid>div,.sdr-evidence>div')){const l=tile.querySelector('span')?.textContent?.trim();if(l==='現價'||l==='收盤'){const v=tile.querySelector('b')?.textContent?.trim();if(v&&v!=='—')return v}}
  return '—';
}
function parseBandCenter(band){const nums=(String(band||'').replace(/,/g,'').match(/\d+(?:\.\d+)?/g)||[]).map(Number).filter(Number.isFinite);if(!nums.length)return'—';const v=nums.length>1?(nums[0]+nums[1])/2:nums[0];return v.toLocaleString('zh-TW',{maximumFractionDigits:v<100?2:v<1000?1:0})}
function directModel(card,fallback){
  const rank=card.querySelector('.isd-zone-head span')?.textContent?.trim()||fallback;
  const title=card.querySelector('.isd-zone-head b')?.textContent?.trim()||labels[rank]||rank;
  const band=card.querySelector('.isd-zone-price')?.textContent?.trim()||'—';
  const raw=[...card.querySelectorAll('small')].map(x=>x.textContent.trim()).join('｜');
  const parts=raw.split('｜').map(x=>x.trim()).filter(Boolean);
  const dist=(parts.find(x=>/^距離/.test(x))||'').replace(/^距離\s*/,'')||'—';
  const strengthRaw=(parts.find(x=>/^強度/.test(x))||'').replace(/^強度\s*/, '');
  const strength=Number(strengthRaw);
  const evidenceText=parts.filter(x=>!/^距離/.test(x)&&!/^強度/.test(x)).join('＋')||'結構區';
  const evidenceCount=evidenceText.split(/[＋+]/).map(x=>x.trim()).filter(Boolean).length;
  return{rank,title,band,center:parseBandCenter(band),dist,strength:Number.isFinite(strength)?strength:null,evidenceText,evidenceCount};
}
function stars(n){if(!Number.isFinite(n))return'☆☆☆☆☆';const k=Math.max(0,Math.min(5,Math.round(n)));return'★'.repeat(k)+'☆'.repeat(5-k)}
function rule(side){return side==='resistance'
  ?'<div class="pm-rule"><p><b>確認：</b>有效站上壓力上緣，量價同步，之後回測不破才算確認。</p><p><b>假突破：</b>突破後若快速跌回壓力帶下方且無法站回，視為假突破，恢復壓力角色。</p></div>'
  :'<div class="pm-rule"><p><b>確認：</b>回測價格帶守住，重新站回上緣；量縮回測優先。</p><p><b>失效：</b>不因單一刺穿判定失守；連續兩根對應週期 K 收在下緣下方，或跌破後反抽站不回且量價轉弱，才視為結構失效。</p></div>'}
function directCard(m,side){return `<div class="pm-card"><div class="pm-card-head"><div class="pm-card-title"><span class="pm-rank">${esc(m.rank)}</span><span>${esc(labels[m.rank]||m.title)}</span></div><span class="pm-state">有效結構</span></div><div class="pm-price-row"><div><div class="pm-center">${esc(m.center)}</div><div class="pm-band">價格帶 ${esc(m.band)}</div></div><div class="pm-distance">距現價<b>${esc(m.dist)}</b></div></div><div class="pm-evidence">${esc(m.evidenceText)}</div><div class="pm-stars">${esc(stars(m.strength))} · ${esc(m.evidenceCount)} 項共振</div>${rule(side)}</div>`}
function empty(rank){return `<div class="pm-empty">${rank} ${labels[rank]}：目前沒有可信結構</div>`}
function laneDirect(title,tone,cards,ranks){const w=document.createElement('div');w.className=`pm-lane ${tone}`;w.innerHTML=`<div class="pm-lane-label">${title}</div>`;for(const r of ranks){const c=cards.find(x=>(x.querySelector('.isd-zone-head span')?.textContent||'').trim()===r);w.insertAdjacentHTML('beforeend',c?directCard(directModel(c,r),tone==='break'?'resistance':'support'):empty(r))}return w}
function laneSr2(title,tone,cards,ranks){const w=document.createElement('div');w.className=`pm-lane ${tone}`;w.innerHTML=`<div class="pm-lane-label">${title}</div>`;for(const r of ranks){const c=cards.find(x=>rankFromSr2(x)===r);if(c){relabelSr2(c);w.appendChild(c)}else w.insertAdjacentHTML('beforeend',empty(r))}return w}
function shell(body){const map=document.createElement('div');map.className=`detail-block ${MAP_CLASS}`;map.innerHTML='<div class="pm-head"><small>INUKO PRICE MAP</small><h3>關鍵價位地圖</h3><p>上方看突破、下方看防守；沒有可信結構就留白，不硬猜價位。</p></div>';return map}
function addNow(map,body){const now=document.createElement('div');now.className='pm-now';now.innerHTML=`<span>NOW</span><b>現價 ${esc(current(body))}</b><small>先看最近的 R1 / S1，再規劃突破或回測劇本</small>`;map.appendChild(now)}
function addFoot(map){const foot=document.createElement('div');foot.className='pm-foot';foot.textContent='S1 / S2 是防守層，R1 / R2 是突破層；這是規劃工具，不代表買進指令。';map.appendChild(foot)}
function decorateDirect(body){
  const sections=[...body.querySelectorAll(':scope > .isd-section')];
  const sr=sections.find(x=>/支撐\s*[\/／|]\s*壓力/.test(x.querySelector(':scope > h3')?.textContent||''));
  if(!sr)return false;
  const supports=[...sr.querySelectorAll('.isd-zone.support')],resists=[...sr.querySelectorAll('.isd-zone.resistance')];
  const map=shell(body);map.classList.add('isd-section');map.appendChild(laneDirect('上方・突破路徑','break',resists,['R2','R1']));addNow(map,body);map.appendChild(laneDirect('下方・防守路徑','defend',supports,['S1','S2']));addFoot(map);sr.replaceWith(map);return true;
}
function decorateSr2(body){
  const blocks=[...body.querySelectorAll(':scope > .detail-block')],sb=blocks.find(x=>/^支撐區/.test(x.querySelector('h3')?.textContent?.trim()||'')),rb=blocks.find(x=>/^壓力區/.test(x.querySelector('h3')?.textContent?.trim()||''));if(!sb||!rb)return false;
  const supports=[...sb.querySelectorAll('.sr2-card')],resists=[...rb.querySelectorAll('.sr2-card')],map=shell(body);map.appendChild(laneSr2('上方・突破路徑','break',resists,['R2','R1']));addNow(map,body);map.appendChild(laneSr2('下方・防守路徑','defend',supports,['S1','S2']));addFoot(map);sb.replaceWith(map);rb.remove();return true;
}
function decorate(){style();const body=document.getElementById('detailBody');if(!body||body.querySelector(`.${MAP_CLASS}`))return;if(decorateDirect(body))return;decorateSr2(body)}
function schedule(){requestAnimationFrame(()=>requestAnimationFrame(decorate))}
style();document.addEventListener('radar:detail-core-rendered',schedule);document.addEventListener('radar:detail-rendered',schedule);if(document.readyState!=='loading')schedule();
})();
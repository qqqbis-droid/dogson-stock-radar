(()=>{
'use strict';

const MAP_ID='dogsonPriceMapThemeStyle';
const STATE_COPY={
  '測試中':'正在測線',
  '接近':'接近關鍵帶',
  '有效結構':'結構有效',
  '已失效':'結構已破'
};
const LABELS={
  R2:'延伸突破帶',
  R1:'第一突破帶',
  S1:'第一防守帶',
  S2:'深層防守帶'
};

function injectStyle(){
  if(document.getElementById(MAP_ID))return;
  const s=document.createElement('style');
  s.id=MAP_ID;
  s.textContent=`
.dogson-price-map{padding:0!important;border:0!important;background:transparent!important;overflow:visible}
.pm-map-head{padding:14px 15px 13px;border-radius:17px;background:linear-gradient(135deg,#203d35 0%,#2f5548 100%);color:#fff;box-shadow:0 8px 22px rgba(28,54,46,.12)}
.pm-map-kicker{font-size:.61rem;letter-spacing:.13em;font-weight:850;opacity:.68}.pm-map-head h3{margin:3px 0 4px!important;color:#fff!important;font-size:1.03rem!important}.pm-map-head p{margin:0;font-size:.7rem;line-height:1.48;opacity:.78}
.pm-map-legend{display:flex;gap:12px;align-items:center;margin-top:9px;font-size:.65rem;opacity:.88}.pm-dot{display:inline-block;width:7px;height:7px;border-radius:99px;margin-right:5px}.pm-dot.break{background:#d3a060}.pm-dot.defend{background:#78b49e}
.pm-lane{position:relative;display:grid;gap:8px;margin-top:10px;padding-left:14px}.pm-lane:before{content:'';position:absolute;left:4px;top:8px;bottom:8px;width:2px;border-radius:2px;background:var(--line)}.pm-lane-label{font-size:.65rem;font-weight:850;letter-spacing:.05em;color:var(--muted);margin:0 0 -1px 1px}.pm-lane.break .pm-lane-label{color:#9a642f}.pm-lane.defend .pm-lane-label{color:#326a59}
.pm-zone.sr2-card{position:relative;border-left:0!important;border-radius:13px!important;padding:10px 11px 10px 12px!important;box-shadow:none!important}.pm-zone.sr2-card:before{content:'';position:absolute;left:-14px;top:20px;width:10px;height:10px;border-radius:50%;border:2px solid var(--card);box-shadow:0 0 0 1px var(--line)}
.pm-zone.pm-break{border:1px solid rgba(176,111,49,.22)!important;background:linear-gradient(135deg,rgba(201,145,78,.105),rgba(255,255,255,.02))!important}.pm-zone.pm-break:before{background:#bd7b3f}.pm-zone.pm-defend{border:1px solid rgba(53,112,92,.22)!important;background:linear-gradient(135deg,rgba(72,133,111,.10),rgba(255,255,255,.02))!important}.pm-zone.pm-defend:before{background:#3f7e69}
.pm-zone .sr2-name{display:flex;align-items:center;gap:7px;font-size:.78rem!important}.pm-rank{display:inline-flex;min-width:29px;height:22px;align-items:center;justify-content:center;border-radius:7px;font-size:.65rem;letter-spacing:.04em;font-weight:900;background:rgba(255,255,255,.72);border:1px solid rgba(80,95,87,.12)}.pm-break .pm-rank{color:#8b5728}.pm-defend .pm-rank{color:#285f4e}.pm-zone .sr2-state{background:transparent!important;border:1px solid rgba(90,106,98,.16);padding:3px 7px!important}
.pm-zone .sr2-main{margin:8px 0 3px!important}.pm-zone .sr2-price{font-size:1.36rem!important;letter-spacing:-.015em}.pm-zone .sr2-band:before{content:'作用區間 ';font-weight:700;color:var(--ink)}.pm-zone .sr2-band{font-size:0!important}.pm-zone .sr2-band::after{content:attr(data-range);font-size:.69rem;color:var(--muted);font-weight:500}.pm-zone .sr2-distance{font-size:.7rem!important;line-height:1.35;color:var(--muted)}.pm-zone .sr2-evidence{margin-top:7px!important;padding-top:7px;border-top:1px solid rgba(90,106,98,.10);font-size:.7rem!important}.pm-zone .sr2-evidence:before{content:'結構依據  ';font-size:.62rem;font-weight:850;letter-spacing:.04em;color:var(--muted)}.pm-zone .sr2-strength{font-size:.66rem!important}.pm-zone .sr2-rule{font-size:.67rem!important;line-height:1.55!important;margin-top:7px!important;padding-top:7px!important}
.pm-current{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;align-items:center;margin:11px 0 5px;padding:10px 12px;border-radius:14px;background:#243e35;color:#fff;box-shadow:0 5px 14px rgba(27,50,42,.12)}.pm-current-badge{grid-row:1/3;display:inline-flex;align-items:center;justify-content:center;height:28px;min-width:44px;padding:0 8px;border-radius:9px;background:rgba(255,255,255,.12);font-size:.62rem;font-weight:900;letter-spacing:.08em}.pm-current strong{font-size:.91rem}.pm-current small{font-size:.67rem;opacity:.74;line-height:1.3}
.pm-empty-zone{position:relative;padding:9px 11px;border:1px dashed var(--line);border-radius:12px;color:var(--muted);font-size:.69rem;background:var(--soft)}.pm-empty-zone:before{content:'';position:absolute;left:-14px;top:15px;width:8px;height:8px;border-radius:50%;background:var(--line);border:2px solid var(--card)}
.pm-map-foot{margin-top:10px;padding:9px 11px;border-radius:11px;background:var(--soft);color:var(--muted);font-size:.66rem;line-height:1.5}.pm-map-foot b{color:var(--ink)}
[data-theme='dark'] .pm-map-head{background:linear-gradient(135deg,#1b302a,#29483e)}[data-theme='dark'] .pm-current{background:#d8e5de;color:#183029}[data-theme='dark'] .pm-current-badge{background:rgba(24,48,41,.09)}[data-theme='dark'] .pm-rank{background:rgba(255,255,255,.055);border-color:rgba(255,255,255,.08)}
@media(max-width:520px){.pm-map-head{padding:13px}.pm-current{grid-template-columns:auto 1fr}.pm-zone .sr2-price{font-size:1.28rem!important}}
`;
  document.head.appendChild(s);
}

function rankOf(card){
  const txt=card?.querySelector('.sr2-name')?.textContent||'';
  return (txt.match(/\b([SR][12])\b/)||[])[1]||'';
}
function distanceOf(card){
  const txt=card?.querySelector('.sr2-distance')?.textContent||'';
  const m=txt.match(/([+-]?\d+(?:\.\d+)?)\s*%/);
  return m?Number(m[1]):null;
}
function numberText(v){
  if(!Number.isFinite(v))return '—';
  return v.toLocaleString('zh-TW',{maximumFractionDigits:v<100?2:1});
}
function currentPrice(body,cards){
  const tiles=[...body.querySelectorAll('.sdr-evidence>div')];
  const tile=tiles.find(x=>['現價','收盤'].includes(x.querySelector('span')?.textContent?.trim()));
  const direct=tile?.querySelector('b')?.textContent?.trim();
  if(direct&&direct!=='—')return direct;
  for(const card of cards){
    const center=Number((card.querySelector('.sr2-price')?.textContent||'').replace(/,/g,''));
    const d=distanceOf(card);
    if(Number.isFinite(center)&&Number.isFinite(d)&&1+d/100!==0)return numberText(center/(1+d/100));
  }
  return '—';
}
function mapStatus(byRank){
  const s1=byRank.S1,dS=distanceOf(s1),r1=byRank.R1,dR=distanceOf(r1);
  if(Number.isFinite(dR)&&dR<0)return '已越過第一突破帶，重點看回測能否守住';
  if(Number.isFinite(dS)&&dS>0)return '已落到第一防守帶下方，先看能否重新站回';
  if(Number.isFinite(dR)&&Math.abs(dR)<=1.2)return '正在靠近第一突破帶，等站穩再確認';
  if(Number.isFinite(dS)&&Math.abs(dS)<=1.2)return '正在靠近第一防守帶，觀察承接是否有效';
  if(s1&&r1)return '現價位於防守帶與突破帶之間，先等下一個訊號';
  if(r1)return '上方突破帶已建立；下方防守結構仍在補強';
  if(s1)return '下方防守帶已建立；上方突破結構仍在補強';
  return '目前沒有足夠可信的關鍵價位結構';
}
function relabel(card,rank){
  if(!card||!rank)return;
  card.dataset.pmRank=rank;
  card.classList.add('pm-zone',rank.startsWith('S')?'pm-defend':'pm-break');
  const name=card.querySelector('.sr2-name');
  if(name)name.innerHTML=`<span class="pm-rank">${rank}</span><span>${LABELS[rank]}</span>`;
  const state=card.querySelector('.sr2-state');
  if(state&&STATE_COPY[state.textContent.trim()])state.textContent=STATE_COPY[state.textContent.trim()];
  const band=card.querySelector('.sr2-band');
  if(band){
    const range=band.textContent.replace(/^價格帶\s*/, '').trim();
    band.dataset.range=range||'—';
    band.textContent='';
  }
  const bs=card.querySelectorAll('.sr2-rule b');
  if(bs[0])bs[0].textContent=rank.startsWith('S')?'防守確認：':'突破確認：';
  if(bs[1])bs[1].textContent=rank.startsWith('S')?'結構失效：':'假突破：';
}
function placeholder(rank){
  const el=document.createElement('div');
  el.className='pm-empty-zone';
  el.innerHTML=`<b>${rank} ${LABELS[rank]}</b>　尚未形成可信第二層結構`;
  return el;
}
function lane(label,tone,nodes){
  const wrap=document.createElement('div');
  wrap.className=`pm-lane ${tone}`;
  wrap.innerHTML=`<div class="pm-lane-label">${label}</div>`;
  nodes.forEach(n=>wrap.appendChild(n));
  return wrap;
}
function decorate(){
  injectStyle();
  const body=document.getElementById('detailBody');
  if(!body||body.querySelector('.dogson-price-map'))return;
  const blocks=[...body.querySelectorAll('.detail-block')];
  const supportBlock=blocks.find(x=>/^支撐區/.test(x.querySelector('h3')?.textContent?.trim()||''));
  const resistanceBlock=blocks.find(x=>/^壓力區/.test(x.querySelector('h3')?.textContent?.trim()||''));
  if(!supportBlock||!resistanceBlock)return;

  const cards=[...supportBlock.querySelectorAll('.sr2-card'),...resistanceBlock.querySelectorAll('.sr2-card')];
  const byRank={};
  for(const card of cards){const rank=rankOf(card);if(rank){byRank[rank]=card;relabel(card,rank)}}

  const map=document.createElement('div');
  map.className='detail-block dogson-price-map';
  map.innerHTML=`<div class="pm-map-head"><div class="pm-map-kicker">DOGSON PRICE MAP</div><h3>關鍵價位地圖</h3><p>上方看突破、下方看防守；沒有可信結構就留白，不硬猜價位。</p><div class="pm-map-legend"><span><i class="pm-dot break"></i>突破帶</span><span><i class="pm-dot defend"></i>防守帶</span></div></div>`;

  const breakNodes=[byRank.R2||placeholder('R2'),byRank.R1||placeholder('R1')];
  map.appendChild(lane('上方・突破路徑','break',breakNodes));

  const now=document.createElement('div');
  now.className='pm-current';
  now.innerHTML=`<span class="pm-current-badge">NOW</span><strong>現價 ${currentPrice(body,cards)}</strong><small>${mapStatus(byRank)}</small>`;
  map.appendChild(now);

  const defendNodes=[byRank.S1||placeholder('S1'),byRank.S2||placeholder('S2')];
  map.appendChild(lane('下方・防守路徑','defend',defendNodes));

  const foot=document.createElement('div');
  foot.className='pm-map-foot';
  foot.innerHTML='<b>怎麼用：</b>S1／S2 是防守層，R1／R2 是突破層。這張圖用來規劃回測、突破與失效劇本，不代表買進指令；第二層不額外灌分。';
  map.appendChild(foot);

  supportBlock.replaceWith(map);
  resistanceBlock.remove();
}

function boot(){
  injectStyle();
  const body=document.getElementById('detailBody');
  if(!body)return;
  new MutationObserver(()=>decorate()).observe(body,{childList:true,subtree:true});
  decorate();
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});
else boot();
})();

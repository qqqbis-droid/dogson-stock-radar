(()=>{
'use strict';
if(window.__INUKO_PORTFOLIO_INTEL_V1__)return;
window.__INUKO_PORTFOLIO_INTEL_V1__=true;
if(!/\/v2(?:\/|$)/.test(location.pathname))return;

const CACHE={build:'',manifest:null,data:new Map(),rendering:false,timer:null};
const STAGE={OBSERVE:'觀察',SETUP:'蓄勢',LAUNCH:'剛啟動',TREND:'趨勢持有',PULLBACK_TEST:'回踩觀察',PULLBACK_CONFIRMED:'回踩承接',WEAKENING:'轉弱警戒',FAILED:'結構失效'};
const ACTION={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先處理風險',DATA_STALE:'資料待更新'};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const fmt=(v,d=1)=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const pct=(v,d=1)=>n(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,d)}%`;
function tick(p){const x=Math.abs(Number(p));if(x<10)return .01;if(x<50)return .05;if(x<100)return .1;if(x<500)return .5;if(x<1000)return 1;return 5}
function price(v){const x=n(v);if(x==null)return'—';const t=tick(x),y=Math.round((x+Number.EPSILON)/t)*t,d=t<.1?2:t<1?1:0;return y.toLocaleString('zh-TW',{maximumFractionDigits:d})}
function range(z){if(!z)return'—';const lo=n(z.low),hi=n(z.high);if(lo==null&&hi==null)return'—';if(lo===hi)return price(z.center??lo);return `${price(lo)}–${price(hi)}`}
function dist(from,to){const a=n(from),b=n(to);return a==null||b==null||b===0?null:(a-b)/b*100}
async function getJson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function manifest(){const m=await getJson(`./data/current_manifest.json?t=${Date.now()}`);if(CACHE.build!==m.active_build_id){CACHE.build=m.active_build_id;CACHE.data.clear()}CACHE.manifest=m;return m}
async function dataset(m,key){const meta=m.datasets?.[key];if(!meta)return null;const ck=`${m.active_build_id}:${key}`;if(CACHE.data.has(ck))return CACHE.data.get(ck);const x=await getJson(meta.url);if(x?.build_id&&x.build_id!==m.active_build_id)throw new Error(`${key} build mismatch`);CACHE.data.set(ck,x);return x}

function style(){if($('#inukoPortfolioIntelStyle'))return;const s=document.createElement('style');s.id='inukoPortfolioIntelStyle';s.textContent=`
.inuko-pintel{margin:10px 0 13px}.inuko-pintel-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:0 0 8px}.inuko-pintel-head b{font-size:.9rem}.inuko-pintel-head small{color:var(--muted);font-size:.66rem}.inuko-priority{display:grid;gap:7px}.inuko-priority-row{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center;padding:9px 10px;border:1px solid var(--line);border-radius:11px;background:var(--card)}.inuko-priority-row .code{font-weight:900;font-size:.78rem}.inuko-priority-row .why{font-size:.7rem;line-height:1.4;color:var(--muted)}.inuko-priority-row .tag{font-size:.62rem;font-weight:850;padding:3px 7px;border-radius:999px;background:var(--soft);white-space:nowrap}.inuko-priority-row.risk .tag{color:#9b3f36;background:#fff1ef}.inuko-priority-row.watch .tag{color:#8a681d;background:#fff8df}.inuko-priority-row.good .tag{color:#276451;background:#eef8f3}.inuko-port-intel-card{margin:9px 0 2px;padding:10px;border:1px solid var(--line);border-radius:12px;background:linear-gradient(180deg,var(--soft),var(--card))}.inuko-port-intel-title{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:7px}.inuko-port-intel-title b{font-size:.76rem}.inuko-port-intel-title .tone{font-size:.62rem;font-weight:850;padding:3px 7px;border-radius:999px;background:var(--soft)}.inuko-port-intel-title .tone.good{color:#276451;background:#edf8f3}.inuko-port-intel-title .tone.watch{color:#85631c;background:#fff8df}.inuko-port-intel-title .tone.risk{color:#963e36;background:#fff0ee}.inuko-intel-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.inuko-intel-grid>div{padding:7px 8px;border-radius:9px;background:var(--card);border:1px solid var(--line)}.inuko-intel-grid span{display:block;font-size:.62rem;color:var(--muted)}.inuko-intel-grid b{display:block;margin-top:2px;font-size:.76rem;line-height:1.3}.inuko-intel-grid small{display:block;margin-top:2px;font-size:.61rem;color:var(--muted);line-height:1.35}.inuko-plan{margin-top:7px;padding:8px 9px;border-radius:9px;background:#fffaf0;font-size:.69rem;line-height:1.5;color:#62522c}.inuko-plan b{color:inherit}.inuko-data-note{margin-top:6px;font-size:.61rem;color:var(--muted);line-height:1.35}.inuko-concentration{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.inuko-concentration span{padding:4px 7px;border-radius:999px;background:var(--soft);font-size:.62rem;color:var(--muted)}
@media(max-width:430px){.inuko-priority-row{grid-template-columns:auto 1fr}.inuko-priority-row .tag{grid-column:2;justify-self:start}.inuko-intel-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
`;document.head.appendChild(s)}

function byRank(zones,ids,rank){const set=new Set(ids||[]);return zones.find(z=>set.has(z.zone_id)&&z.rank===rank)||null}
function currentPrice(d,e){return n(d?.quote?.price)??n(e?.close)}
function benchmark(d,indexQuote){return d?.market==='上櫃'?indexQuote?.otc:indexQuote?.taiex}
function relativeInfo(d,e,indexQuote){const stock=n(e?.day_change)??n(d?.quote?.day_change_pct),bench=n(benchmark(d,indexQuote)?.change_pct);if(stock==null||bench==null)return{label:'待補',delta:null,sub:'缺少同日指數'};const delta=stock-bench;return{label:delta>=1?'強於大盤':delta<=-1?'弱於大盤':'接近大盤',delta,sub:`個股 ${pct(stock)}｜指數 ${pct(bench)}`}}
function technical(e,px){if(!e)return{label:'待補',tone:'watch',sub:'技術證據未建立'};const m5=n(e.ma5),m10=n(e.ma10),m20=n(e.ma20),rsi=n(e.rsi),macd=n(e.macd_h),p=n(px)??n(e.close);let label='結構中性',tone='watch';if(p!=null&&m5!=null&&m10!=null&&m20!=null&&p>m5&&m5>m10&&m10>m20){label='均線多頭';tone='good'}else if(p!=null&&m20!=null&&p<m20){label='跌到20MA下';tone='risk'}else if(m5!=null&&m10!=null&&m20!=null&&m5>=m10&&m10>=m20){label='均線偏多';tone='good'}const parts=[];if(rsi!=null)parts.push(`RSI ${fmt(rsi,0)}`);if(macd!=null)parts.push(`MACD柱 ${macd>0?'+':''}${fmt(macd,2)}`);if(n(e.vol_x)!=null)parts.push(`量比 ${fmt(e.vol_x,2)}x`);return{label,tone,sub:parts.join('｜')||'指標待補'}}
function chip(e){if(!e)return{label:'待補',tone:'watch',sub:'籌碼證據未建立'};let s=0,known=0;const f3=n(e.foreign_3d_net),fl=n(e.foreign_net_latest),sbl=n(e.sbl_3change_pct),mg=n(e.margin_3d_pct);if(f3!=null){known++;s+=f3>0?1:f3<0?-1:0}if(fl!=null){known++;s+=fl>0?.6:fl<0?-.6:0}if(sbl!=null){known++;s+=sbl<0?.7:sbl>5?-.7:0}if(mg!=null){known++;s+=mg<=0?.4:mg>5?-.5:0}const label=!known?'待補':s>=1.2?'籌碼改善':s<=-.8?'籌碼轉弱':'籌碼中性';const tone=label==='籌碼改善'?'good':label==='籌碼轉弱'?'risk':'watch';const parts=[];if(f3!=null)parts.push(`外資3日 ${f3>0?'+':''}${fmt(f3/1000,0)}張`);if(sbl!=null)parts.push(`借券3日 ${pct(sbl)}`);if(mg!=null)parts.push(`融資3日 ${pct(mg)}`);return{label,tone,sub:parts.join('｜')||'籌碼待補'}}

const STRUCT_RE=/突破平台|前波高|前波低|20日高|20日低|60日高|60日低|成交密集|大量成交|大量區|缺口|箱型|頸線|前高|前低/;
function zoneEvidence(z){return (z?.evidence||[]).map(String).filter(Boolean)}
function zoneMeta(z){
  if(!z)return '待補';
  const conf=n(z.confidence),ev=zoneEvidence(z).slice(0,3);
  const bits=[`${z.rank||''} ${range(z)}`.trim()];
  if(conf!=null)bits.push(`可信 ${fmt(conf,0)}%`);
  if(ev.length)bits.push(ev.join('＋'));
  return bits.join('｜');
}
function originPoint(d,e,s1,s2){
  const candidates=[s1,s2].filter(Boolean).map(z=>{
    const ev=zoneEvidence(z),struct=ev.filter(x=>STRUCT_RE.test(x));
    const conf=n(z.confidence)??0,center=n(z.center)??n(z.high);
    const families=z.evidence_families||[];
    const score=(struct.length?4:0)+(families.includes('price_structure')?3:0)+(families.includes('volume_structure')?2:0)+conf/100+(z.rank==='S2'?.15:0);
    return{z,ev,struct,conf,center,score};
  }).filter(x=>x.center!=null&&x.struct.length&&x.conf>=55);
  if(candidates.length){
    candidates.sort((a,b)=>b.score-a.score||b.conf-a.conf);
    const c=candidates[0];
    return{price:c.center,source:c.struct.slice(0,2).join('＋'),kind:'起漲結構基準',confidence:c.conf,fallback:false};
  }
  const ma20=n(e?.ma20);
  if(ma20!=null)return{price:ma20,source:'20MA',kind:'20MA 趨勢基準',confidence:null,fallback:true};
  return null;
}
function extension(p,px,origin){
  if(!origin||px==null)return{label:'資料不足',tone:'watch',sub:'目前沒有可用的結構或20MA基準',fallback:true};
  const now=dist(px,origin.price),cost=dist(n(p.avg_cost),origin.price);
  if(origin.fallback){
    const tone=now!=null&&Math.abs(now)>=12?'watch':'good';
    return{label:'趨勢基準',tone,now,cost,fallback:true,sub:`20MA ${price(origin.price)}｜現價 ${pct(now)}｜成本 ${pct(cost)}｜非起漲點`,source:origin.source};
  }
  let tone='good',label='接近起漲基準';
  if(now!=null&&now>=20){tone='risk';label='明顯延伸'}else if(now!=null&&now>=10){tone='watch';label='已有延伸'}
  return{label,tone,now,cost,fallback:false,sub:`基準 ${price(origin.price)}｜現價 ${pct(now)}｜成本 ${pct(cost)}｜${origin.source}`,source:origin.source};
}
function supportState(px,s1){if(!s1||px==null)return{label:'支撐待補',tone:'watch',sub:'S1 尚未建立'};const d=n(s1.distance_pct)??dist(n(s1.center),px);const near=Math.abs(d??99)<=3;return{label:near?'接近 S1':'S1 尚有空間',tone:near?'watch':'good',sub:`${zoneMeta(s1)}｜距現價 ${pct(d)}`}}
function resistanceState(px,r1){if(!r1||px==null)return{label:'上方壓力待補',tone:'watch',sub:'R1 尚未建立'};const d=n(r1.distance_pct)??dist(n(r1.center),px);const near=Math.abs(d??99)<=3;return{label:near?'接近 R1':'R1 尚有空間',tone:near?'watch':'good',sub:`${zoneMeta(r1)}｜距現價 ${pct(d)}`}}
function reasonState(p,d){if(p.reason_status==='INVALID')return{label:'❌ 進場理由失效',tone:'risk'};if(p.reason_status==='WEAKENING')return{label:'⚠️ 進場理由弱化',tone:'watch'};if(['FAILED','WEAKENING'].includes(d?.lifecycle_stage)||['EXIT_PRIORITY','REDUCE_WATCH'].includes(d?.action_state))return{label:'⚠️ 理由仍在、結構轉弱',tone:'risk'};return{label:'✅ 進場理由成立',tone:'good'}}
function plan(p,d,e,px,s1,r1,ext,rel,ch){
  const sLow=n(s1?.low),sHigh=n(s1?.high),rHigh=n(r1?.high),rLow=n(r1?.low);
  if(p.reason_status==='INVALID')return'核心進場理由已失效：先檢查減碼／退出，不因虧損直接攤平。';
  if(['FAILED','WEAKENING'].includes(d?.lifecycle_stage)||['EXIT_PRIORITY','REDUCE_WATCH'].includes(d?.action_state))return sLow!=null?`先守 ${price(sLow)} 附近結構；不是瞬間刺穿就砍，而是有效跌破、反抽站不回且量價轉弱時優先減碼。`:'結構已轉弱：暫不加碼，等重新站回關鍵結構再評估。';
  if(s1&&Math.abs(n(s1.distance_pct)??99)<=3)return`回測 ${range(s1)} 若量縮守住、重新站回上緣可續抱；若有效跌破下緣 ${price(sLow)} 且反抽不回，再處理減碼。`;
  if(r1&&Math.abs(n(r1.distance_pct)??99)<=3)return ext.tone==='risk'?`已接近 ${range(r1)} 且位階延伸；先不追著加碼。有效站上 ${price(rHigh)}、量價同步且回測不破，再看續抱；否則優先保護獲利。`:`先看 ${range(r1)} 是否有效突破；站上 ${price(rHigh)} 且回測不破才算確認，碰壓力但站不穩就不追。`;
  if(rel.tone==='risk'||ch.tone==='risk')return'S1 未失守前可續觀察，但相對強弱／籌碼轉弱，暫停加碼；等結構與籌碼至少一項重新改善。';
  if(d?.action_state==='ADD_ON_CONFIRM')return rHigh!=null?`只在站上 ${price(rHigh)} 且量價確認後考慮加碼；沒有確認就續抱，不追高。`:'只在系統確認條件成立後考慮加碼；沒有確認就續抱。';
  return sHigh!=null&&rLow!=null?`目前位於 ${price(sHigh)} 支撐上緣與 ${price(rLow)} 壓力下緣之間：守支撐續抱，突破壓力再提高進攻性。`:'目前核心理由未失效：維持續抱觀察，等支撐／壓力結構更清楚再動作。';
}
function priorityScore(x){let s=0;if(x.reason.tone==='risk')s+=5;else if(x.reason.tone==='watch')s+=3;if(x.tech.tone==='risk')s+=3;if(x.chip.tone==='risk')s+=2;if(x.rel.tone==='risk')s+=2;if(x.sup.tone==='watch')s+=1.5;if(x.res.tone==='watch')s+=1;if(x.ext.tone==='risk')s+=1;return s}
function priorityLabel(x){if(x.reason.tone==='risk'||x.tech.tone==='risk')return{tone:'risk',label:'先檢查'};if(x.sup.tone==='watch'||x.res.tone==='watch'||x.reason.tone==='watch'||x.rel.tone==='risk'||x.chip.tone==='risk')return{tone:'watch',label:'今天要看'};return{tone:'good',label:'結構穩定'}}
function priorityWhy(x){const arr=[];if(x.reason.tone!=='good')arr.push(x.reason.label.replace(/[✅⚠️❌]\s*/g,''));if(x.sup.tone==='watch')arr.push('接近支撐');if(x.res.tone==='watch')arr.push('接近壓力');if(x.rel.tone==='risk')arr.push('弱於大盤');if(x.chip.tone==='risk')arr.push('籌碼轉弱');if(x.ext.tone==='risk')arr.push('位階延伸');if(!arr.length)arr.push('目前沒有明顯警訊');return arr.slice(0,3).join('・')}
function tile(label,main,sub=''){return `<div><span>${esc(label)}</span><b>${esc(main)}</b>${sub?`<small>${esc(sub)}</small>`:''}</div>`}
function cardBlock(x){
  const overall=priorityLabel(x);
  const srMain=`${range(x.s1)} / ${range(x.r1)}`;
  const srSub=`${x.sup.sub}${x.res.sub?`；${x.res.sub}`:''}`;
  return `<div class="inuko-port-intel-card" data-inuko-intel="1"><div class="inuko-port-intel-title"><b>犬子持倉健檢</b><span class="tone ${overall.tone}">${esc(overall.label)}</span></div><div class="inuko-intel-grid">${tile('進場理由',x.reason.label,`${ACTION[x.d?.action_state]||x.d?.action_state||'—'}｜${STAGE[x.d?.lifecycle_stage]||x.d?.lifecycle_stage||'—'}`)}${tile('位階 / 起漲',x.ext.label,x.ext.sub)}${tile('技術結構',x.tech.label,x.tech.sub)}${tile('相對大盤',x.rel.label,x.rel.delta==null?x.rel.sub:`相對 ${pct(x.rel.delta)}`)}${tile('籌碼變化',x.chip.label,x.chip.sub)}${tile('支撐 / 壓力',srMain,srSub)}</div><div class="inuko-plan"><b>若 A → B：</b>${esc(x.plan)}</div><div class="inuko-data-note">資料日 ${esc(x.tradeDate||'—')}。支撐／壓力顯示多證據融合後的 S1/R1 與可信度；起漲只在價格／量價結構足夠時顯示，否則以 20MA 趨勢基準替代並明確標示「非起漲點」。</div></div>`;
}
function makeModel(p,d,e,zones,indexQuote,tradeDate){
  const px=currentPrice(d,e),s1=byRank(zones,d?.support_zone_ids,'S1'),s2=byRank(zones,d?.support_zone_ids,'S2'),r1=byRank(zones,d?.resistance_zone_ids,'R1'),r2=byRank(zones,d?.resistance_zone_ids,'R2');
  const origin=originPoint(d,e,s1,s2),ext=extension(p,px,origin),tech=technical(e,px),ch=chip(e),rel0=relativeInfo(d,e,indexQuote),rel={...rel0,tone:rel0.delta==null?'watch':rel0.delta<=-1?'risk':rel0.delta>=1?'good':'watch'},reason=reasonState(p,d),sup=supportState(px,s1),res=resistanceState(px,r1);
  const x={p,d,e,px,s1,s2,r1,r2,origin,ext,tech,chip:ch,rel,reason,sup,res,tradeDate};
  x.plan=plan(p,d,e,px,s1,r1,ext,rel,ch);x.score=priorityScore(x);return x;
}
function ensureSummary(models,positions){const cards=$('#portfolioCards');if(!cards)return;let root=$('#inukoPortfolioIntel');if(!root){root=document.createElement('section');root.id='inukoPortfolioIntel';root.className='inuko-pintel';cards.insertAdjacentElement('beforebegin',root)}const sorted=models.slice().sort((a,b)=>b.score-a.score||a.p.code.localeCompare(b.p.code));const top=sorted.slice(0,Math.min(4,sorted.length));const totalCost=positions.reduce((s,p)=>s+(n(p.avg_cost)||0)*(n(p.shares)||0),0);const stockConcentration=positions.map(p=>({code:p.code,w:totalCost>0?(n(p.avg_cost)||0)*(n(p.shares)||0)/totalCost*100:0})).sort((a,b)=>b.w-a.w)[0];const groups=new Map();for(const x of models){const cost=(n(x.p.avg_cost)||0)*(n(x.p.shares)||0),g=x.d?.primary_group||'待分類';groups.set(g,(groups.get(g)||0)+cost)}const groupTop=[...groups].map(([g,c])=>({g,w:totalCost>0?c/totalCost*100:0})).sort((a,b)=>b.w-a.w)[0];root.innerHTML=`<div class="inuko-pintel-head"><b>今天最需要看</b><small>${esc(models[0]?.tradeDate||'')} 持倉健檢</small></div><div class="inuko-priority">${top.map(x=>{const t=priorityLabel(x);return `<div class="inuko-priority-row ${t.tone}"><span class="code">${esc(x.p.code)} ${esc(x.p.name||x.d?.name||'')}</span><span class="why">${esc(priorityWhy(x))}</span><span class="tag">${esc(t.label)}</span></div>`}).join('')}</div><div class="inuko-concentration">${stockConcentration?`<span>最大單檔 ${esc(stockConcentration.code)} ${fmt(stockConcentration.w,1)}%</span>`:''}${groupTop?`<span>最大族群 ${esc(groupTop.g)} ${fmt(groupTop.w,1)}%</span>`:''}${stockConcentration?.w>30?'<span>⚠️ 單檔集中度偏高</span>':''}${groupTop?.w>45?'<span>⚠️ 族群集中度偏高</span>':''}</div>`}

async function loadData(){const m=await manifest();const [idx,detail,zones,evidence,indexQuote]=await Promise.all([dataset(m,'decision_close_index'),dataset(m,'decision_close_detail'),dataset(m,'zone_close'),dataset(m,'stock_detail_close'),dataset(m,'index_quote')]);return{m,idx:Array.isArray(idx)?idx:[],detail:detail?.items||{},zones:Array.isArray(zones)?zones:[],evidence:evidence?.items||{},indexQuote:indexQuote||null}}
async function render(){if(CACHE.rendering)return;const tab=document.querySelector('.tab.active')?.dataset.view;if(tab!=='portfolio')return;const store=window.RadarPortfolioStore,cards=$('#portfolioCards');if(!store||!cards)return;const positions=store.list?.()||[];if(!positions.length){$('#inukoPortfolioIntel')?.remove();return}CACHE.rendering=true;try{const data=await loadData(),imap=new Map(data.idx.map(x=>[String(x.code),x])),models=positions.map(p=>{const d=imap.get(String(p.code))||data.detail[String(p.code)]||null,e=data.evidence[String(p.code)]||null;return makeModel(p,d,e,data.zones,data.indexQuote,data.m.trade_date)});ensureSummary(models,positions);for(const x of models){const card=[...cards.querySelectorAll('.portfolio-card[data-portfolio-code]')].find(el=>String(el.dataset.portfolioCode||'')===String(x.p.code));if(!card)continue;card.querySelector('.inuko-port-intel-card')?.remove();const anchor=card.querySelector('.action-line')||card.querySelector('.score-row')||card.querySelector('.card-top');anchor?.insertAdjacentHTML('afterend',cardBlock(x))}}catch(err){console.error('INUKO portfolio intel',err)}finally{CACHE.rendering=false}}
function schedule(delay=180){clearTimeout(CACHE.timer);CACHE.timer=setTimeout(render,delay)}
function boot(){style();schedule(450);document.addEventListener('radar:portfolio-changed',()=>schedule(500));document.addEventListener('radar:view-rendered',()=>schedule(250));document.addEventListener('inuko:portfolio-synced',()=>schedule(300));document.addEventListener('click',e=>{if(e.target?.closest?.('.tab[data-view="portfolio"]'))schedule(450)},true)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

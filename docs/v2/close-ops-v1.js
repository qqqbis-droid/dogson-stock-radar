(()=>{'use strict';
// Single source of close decision presentation: enhance the existing #cards,
// never create a duplicate ranking or change Engine scores/rank/order.
if(window.InukoCloseOps?.version==='2.0')return;
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const td=v=>String(v||'').slice(0,10);
const fmt=(v,d=1)=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const tick=x=>x<10?.01:x<50?.05:x<100?.1:x<500?.5:x<1000?1:5;
function pp(v,edge){const x=n(v);if(x==null||x<=0)return'—';const t=tick(x),k=edge==='lower'?Math.floor((x+1e-9)/t):edge==='upper'?Math.ceil((x-1e-9)/t):Math.round(x/t);return fmt(k*t,t<.1?2:t<1?1:0)}
const range=z=>z?pp(z.low,'lower')+'～'+pp(z.high,'upper'):'—';
const D={manifest:null,build:'',date:'',cache:new Map(),pending:new Map(),seq:0,loading:false,mode:'',lastRefresh:0,index:null,peers:null};
const KEY='dogson.close.public-candidate-history.v1';
const screenActive=()=>document.querySelector('.tab.active')?.dataset.view==='close'&&!document.querySelector('#radarPanel')?.classList.contains('h60-screen-active');
const swingActive=()=>screenActive()&&document.querySelector('[data-close-mode="swing"]')?.classList.contains('active');
const validGlobal=()=>window.DOGSON_CLOSE_DECISION_ALLOWED===true&&window.DOGSON_CLOSE_DATA_STATUS?.allowed===true&&window.DOGSON_CLOSE_DATA_STATUS?.strictStale!==true;
const positions=()=>{try{return window.RadarPortfolioStore?.list?.()||[]}catch{return[]}};
function findZones(shard,price,date,build){
 const zs=(Array.isArray(shard?.zones)?shard.zones:[]).filter(z=>z&&z.build_id===build&&td(z.trade_date)===date&&z.structure_state!=='INVALID'&&n(z.low)!=null&&n(z.high)!=null&&z.low>0&&z.high>=z.low);
 const pick=(side,rank)=>{
  const rows=zs.filter(z=>z.side===side&&z.rank===rank);
  return rows.sort((a,b)=>side==='SUPPORT'?b.high-a.high:a.low-b.low)[0]||null
 };
 let support=pick('SUPPORT','S1');
 let resistance=pick('RESISTANCE','R1');
 // Never silently substitute a distant S2/R2 for S1/R1 in the compact card.
 const valid=z=>!!z&&['FRESH','FROZEN'].includes(String(z.freshness||''));
 return {support:valid(support)?support:null,resistance:valid(resistance)?resistance:null,
    supportFresh:valid(support),resistanceFresh:valid(resistance),fresh:valid(support)&&valid(resistance)};
}
function classify(d,shard){
 const ev=shard?.evidence||{},engine=shard?.decision||d||{},code=String(engine.code||d?.code||''),price=n(engine.quote?.price??d?.quote?.price),date=D.date;
 const zones=findZones(shard,price,date,D.build),support=zones.support,resistance=zones.resistance;
 const r=n(support?.low),target=n(resistance?.low);
 const rr=price!=null&&r!=null&&target!=null&&price>r&&target>price?(target-price)/(price-r):null;
 const same=!!shard&&shard.build_id===D.build&&shard.view==='close'&&td(shard.as_of)===date;
 const confidence=n(engine.data_confidence);
 // Price structures are independently valid: R1 may be absent even if S1 is
 // confirmed. Never erase an existing S1 when a separate R1 is missing.
 const sessionOK=validGlobal()&&same&&confidence!=null&&confidence>=80&&price!=null;
 const good=sessionOK&&zones.fresh;
 const riskover=Array.isArray(engine.risk_overlays)?engine.risk_overlays:[];
 const restricted=riskover.some(x=>['TRADING_RESTRICTION','LIQUIDITY_RISK','DATA_QUALITY_RISK'].includes(String(x)));
 const overheated=engine.action_state==='DO_NOT_CHASE'||engine.no_chase===true||riskover.includes('OVERHEAT')||(n(ev.dist20)!=null&&n(ev.dist20)>8);
 const impaired=['EXIT_PRIORITY','REDUCE_WATCH','DATA_STALE'].includes(engine.action_state)||['WEAKENING','FAILED'].includes(engine.lifecycle_stage);
 const peers=D.peers?.get(String(engine.primary_group||d?.primary_group||''))||0;
 const flowDates=[ev.foreign_date,ev.sbl_date].map(td);
 const chip=ev.foreign_3buy===true&&ev.sbl_3down===true&&flowDates.every(x=>x===date);
 const avg=n(ev.avg_turnover20)??(n(ev.avg_turnover20_mn)!=null?n(ev.avg_turnover20_mn)*1e6:null);
 const chipReady=chip&&peers>=3&&avg!=null&&avg>=30000000&&!restricted&&!overheated;
 const early=['SETUP','LAUNCH','PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(engine.lifecycle_stage)&&!overheated&&(n(ev.dist20)==null||n(ev.dist20)<=7);
 const owned=positions().some(p=>String(p.code)===code);
 let type='WATCH',label='暫時觀察',note='尚未出現足夠的進場條件，等待量價與結構同步。',gate='等關鍵條件確認';
 if(!sessionOK){
  type='VERIFY';label='資料待驗證';note=same?'盤後資料信心或全域資料日期尚未確認；已驗證的價位只供參考，不作為下單指令。':'個股盤後來源尚未取得或交易日不一致，暫不使用任何價位下單。';gate='完成同交易日資料核對後再評估';
 }else if(!zones.supportFresh||!zones.resistanceFresh){
  type='PARTIAL';label=!zones.supportFresh?'支撐待補':'壓力待補';
  note=!zones.supportFresh?'沒有有效 S1 支撐，不硬設停損；已有的 R1 僅供觀察。':'同日 S1 已核對，但缺少有效 R1，無法計算進場風報比；不推估突破價。';
  gate='價位證據補齊前，暫不建立新倉';
 }else if(restricted||overheated||impaired){
  type='NO_CHASE';label='先不追價';note=restricted?'有交易限制、流動性或資料品質風險，暫不列新倉。':impaired?'原始結構已轉弱或風險優先，暫不列新倉。':'過熱／不追價條件已成立。';gate='等待風險解除並重新驗證';
 }else if(resistance&&price>=resistance.low){
  type='NO_CHASE';label='先不追價';note='收盤價已接觸第一壓力區；R1 是壓力，不是直接買進價。';gate='突破後回測確認才重新評估';
 }else if(rr!=null&&rr<1.5){
  type='NO_CHASE';label='先不追價';note='收盤價到 R1 的報酬／S1 風險比不足 1.5，位置不具新倉優勢。';gate='等回踩改善風險報酬';
 }else if(['WAIT_PULLBACK','PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(engine.action_state)||['PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(engine.lifecycle_stage)){
  type='LAYOUT';label='等待布局';note='結構可追蹤，但回踩守住與量價確認前不直接買入。';gate='回踩 S1 守住並確認量價';
 }else if(['WAIT_TRIGGER','LAUNCH','SETUP'].includes(engine.action_state)||['LAUNCH','SETUP'].includes(engine.lifecycle_stage)){
  type='BREAKOUT';label='等突破確認';note='尚未證實突破，壓力區站穩後仍需回測與量價確認。';gate='R1 突破後回測不破';
 }else if(early&&engine.actionable===true){
  type='LAYOUT';label='等待布局';note='原模型條件具備，但隔日仍須等價位與量價確認。';gate='等待支撐附近有效承接';
 }
 return {code,type,label,note,gate,owned,rr,support:same?support:null,resistance:same?resistance:null,chipReady,early,confidence,
   ready:good,sessionOK,partial:same&&!zones.fresh,block:restricted,missing:!same,date:D.date};
}
function compact(x){
 const owned=x.owned?'<span class="cp-owned">💼 已持有</span>':'';
 const levels=x.support||x.resistance
  ?'<div class="cp-levels"><div><small>S1 回踩觀察區</small><b>'+esc(x.support?range(x.support):'待補（不推估）')+'</b></div><div><small>R1 第一壓力區</small><b>'+esc(x.resistance?range(x.resistance):'待補（不推估）')+'</b></div></div>'
  :'<div class="cp-message">尚無同日、同版本的有效支撐／壓力價區。</div>';
 const risk=x.support
  ?'有效跌破 S1 下緣 '+pp(x.support.low,'lower')+'，且回抽未能站回，重新評估原結構；不是碰價就停損。'
  :'沒有有效 S1，不設定猜測停損價，暫不開新倉。';
 const cautious=!x.sessionOK
  ?(x.missing?'⛔ 尚無同版本盤後證據；所有價位僅供參考。':'⚠️ 資料日期或信心檢查未通過；不可直接下單。')
  :null;
 const tags=x.ready?[x.early?'🌱 起漲前段觀察':null,x.chipReady?'🔗 籌碼＋同族群共振已核對':null].filter(Boolean):[];
 const rrText=x.ready&&x.rr!=null?' · 風報比 '+fmt(x.rr,2)+' 倍':x.partial?' · 風報比待證據補齊':'';
 return '<section class="close-plan-integrated" data-close-plan aria-label="明日作戰">'
  +owned
  +'<div class="cp-explain">'+esc(x.note)+'</div>'
  +'<div class="cp-plan-row"><span class="cp-plan-label">明日動作</span><b class="cp-plan-value">'+esc(x.gate)+'</b></div>'
  +'<div class="cp-plan-heading">關鍵價位'+esc(rrText)+'</div>'
  +levels
  +'<div class="cp-plan-row cp-plan-risk"><span class="cp-plan-label">失效條件</span><span class="cp-plan-value">'+esc(risk)+'</span></div>'
  +(cautious?'<div class="cp-risk">'+esc(cautious)+'</div>':'')
  +(tags.length?'<div class="cp-tags">'+tags.map(t=>'<span>'+esc(t)+'</span>').join('')+'</div>':'')
  +'<div class="cp-risk">資料日 '+esc(x.date||'—')+' · 隔日須確認即時量價與大盤相對強弱</div>'
  +'</section>';
}
function writeCard(card,x){
 if(!card?.isConnected)return;
 const line=card.querySelector(':scope > .action-line'),label=line?.querySelector('b');
 if(line&&label){
  const tone=x.type==='NO_CHASE'?'risk':x.type==='VERIFY'||x.type==='PARTIAL'?'stale':x.type==='LAYOUT'||x.type==='BREAKOUT'?'wait':'neutral';
  line.classList.remove('go','wait','risk','stale','neutral');line.classList.add(tone);
  label.textContent=x.label;
  const dot=line.querySelector('span');if(dot)dot.textContent=x.type==='VERIFY'?'!':'○';
  const sm=line.querySelector('small');if(sm)sm.textContent='犬子結論 · '+(x.date||'盤後');
 }
 const prior=card.querySelector('[data-close-plan]');
 if(prior){prior.outerHTML=compact(x)}
 else{const score=card.querySelector(':scope > .score-row'),before=card.querySelector(':scope > .reason');if(score)score.insertAdjacentHTML('afterend',compact(x));else if(before)before.insertAdjacentHTML('beforebegin',compact(x));else card.insertAdjacentHTML('beforeend',compact(x))}
 card.dataset.closeDecision=x.type;
}
function explainPending(card){
 if(!card||card.querySelector('[data-close-plan]'))return;
 // Keep the cautious Engine state visible while asynchronously loading the
 // precise S1/R1 decision. Never replace every candidate with one fake status.
 const line=card.querySelector(':scope > .action-line'),label=line?.querySelector('b');
 if(label&&label.textContent.trim()==='明日策略核對中')label.textContent='明日候選・條件待補';
 if(line){line.classList.remove('go');line.classList.add('neutral')}
}
async function manifest(){
 const r=await fetch('./data/current_manifest.json?cp='+Date.now(),{cache:'no-store'});
 if(!r.ok)throw Error('盤後 manifest '+r.status);
 const m=await r.json();if(!m.health?.validation_passed||!m.active_build_id)throw Error('盤後 Atomic Bundle 尚未驗證');
 if(D.build!==m.active_build_id){D.cache.clear();D.pending.clear();D.index=null;D.peers=null}
 D.manifest=m;D.build=m.active_build_id;D.date=td(m.datasets?.decision_close_summary?.as_of);
 if(!D.date)throw Error('缺少盤後交易日');
 return m;
}
async function shard(code,build){
 if(D.cache.has(code))return D.cache.get(code);
 if(D.pending.has(code))return D.pending.get(code);
 const work=(async()=>{try{
  const r=await fetch('./data/builds/'+encodeURIComponent(build)+'/stock-shards/close/'+encodeURIComponent(code)+'.json',{cache:'force-cache'});
  if(!r.ok)return null;const s=await r.json();return s?.build_id===build&&s?.view==='close'&&td(s.as_of)===D.date?s:null;
 }catch{return null}})();
 D.pending.set(code,work);const s=await work;D.pending.delete(code);
 if(build===D.build)D.cache.set(code,s);return s;
}
async function indexForPeers(){
 if(D.index)return;
 const idx=D.manifest?.datasets?.decision_close_index;
 if(!idx?.url)return;
 try{
  const r=await fetch(idx.url,{cache:'force-cache'});if(!r.ok)return;
  const rows=await r.json();if(!Array.isArray(rows)||rows.length>2000)return;
  D.index=rows;
  const counts=new Map();
  for(const d of rows){if((n(d.scores?.swing_quality_score)||0)<65||(n(d.scores?.entry_position_score)||0)<55)continue;
    if(!['SETUP','LAUNCH','PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(d.lifecycle_stage))continue;
    const key=String(d.primary_group||'');if(key)counts.set(key,(counts.get(key)||0)+1)}
  D.peers=counts;
  try{const archives=JSON.parse(localStorage.getItem(KEY)||'[]');let values=Array.isArray(archives)?archives.filter(x=>x?.date!==D.date).slice(-24):[];values.push({date:D.date,rows:rows.filter(x=>n(x.quote?.price)>0).slice(0,60).map(x=>({code:String(x.code),close:n(x.quote.price)}))});localStorage.setItem(KEY,JSON.stringify(values.slice(-24)))}catch{}
 }catch(err){console.warn('close candidate index unavailable',err)}
}
let timer=0,working=false,queued=false,observer=null;
async function refresh(){
 if(!swingActive()){if(observer){observer.disconnect();observer=null}return}
 if(working){queued=true;return}
 working=true;const job=++D.seq;
 try{
  if(!D.manifest||Date.now()-D.lastRefresh>60000){await manifest();D.lastRefresh=Date.now()}
  if(job!==D.seq||!swingActive())return;
  const cards=[...document.querySelectorAll('#cards .card[data-code]:not([data-ignition]):not(.outside-pool)')];
  if(!cards.length)return;
  cards.forEach(explainPending);
  const candidates=cards.map(card=>({card,code:String(card.dataset.code||'')})).filter(x=>x.code);
  // Previously the full 85+ candidate list had to finish ALL network requests
  // before a single card was updated. On iPhone that stranded every card in
  // "checking" mode. Update each visible card as soon as its shard finishes.
  const update=async(card,code)=>{
   if(job!==D.seq||!swingActive()||!card.isConnected)return;
   const item=await shard(code,D.build);
   if(job!==D.seq||!swingActive()||!card.isConnected)return;
   writeCard(card,classify(item?.decision||{code},item));
  };
  if(observer){observer.disconnect();observer=null}
  if(typeof IntersectionObserver==='function'){
   observer=new IntersectionObserver(entries=>{
    for(const entry of entries){
     if(!entry.isIntersecting)continue;
     observer?.unobserve(entry.target);
     const card=entry.target,code=String(card.dataset.code||'');
     if(code)void update(card,code);
    }
   },{rootMargin:'700px 0px',threshold:0});
   for(const {card} of candidates)observer.observe(card);
  }else{
   // Older embedded browsers: small progressive batches, never one final
   // all-cards barrier before rendering verified S1/R1.
   for(let i=0;i<candidates.length;i+=5){
    if(job!==D.seq||!swingActive())return;
    await Promise.allSettled(candidates.slice(i,i+5).map(({card,code})=>update(card,code)));
   }
  }
  if(!D.index)indexForPeers().then(()=>{
   if(job!==D.seq||!swingActive())return;
   for(const card of document.querySelectorAll('#cards .card[data-code]:not([data-ignition]):not(.outside-pool)')){
    const code=card.dataset.code;
    if(D.cache.has(code)&&card.querySelector('[data-close-plan]')){
     const item=D.cache.get(code);
     writeCard(card,classify(item?.decision||{code},item));
    }
   }
  }).catch(()=>{});
 }catch(e){
  console.warn('integrated close plan',e);
  for(const card of document.querySelectorAll('#cards .card[data-code]:not([data-ignition]):not(.outside-pool)'))
   writeCard(card,classify({code:card.dataset.code},null));
 }finally{working=false;if(queued){queued=false;schedule()}}
}
function schedule(){clearTimeout(timer);timer=setTimeout(refresh,65)}
function invalidate(){D.manifest=null;D.build='';D.date='';D.cache.clear();D.index=null;D.peers=null;D.lastRefresh=0;schedule()}
document.addEventListener('radar:cards-rendered',schedule);
document.addEventListener('radar:view-rendered',schedule);
document.addEventListener('radar:data-reloaded',invalidate);
document.addEventListener('radar:afterhours-refresh',schedule);
 document.addEventListener('radar:close-gate-updated',schedule);
document.addEventListener('click',e=>{if(e.target.closest('[data-close-mode],.tab'))setTimeout(schedule,100)});
window.InukoCloseOps={version:'2.0',schedule,get(code){const s=D.cache.get(String(code));return s?classify(s.decision||{},s):null},analyze(shard){return shard?.view==='close'?classify(shard.decision||{},shard):null},isReady(){return validGlobal()}};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
})();
(()=>{'use strict';
if(window.__INUKO_CLOSE_OPS_V1__)return;
window.__INUKO_CLOSE_OPS_V1__=true;
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const fmt=(v,d=1)=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const p=v=>n(v)==null?'—':fmt(v,n(v)<50?2:n(v)<500?1:0);
const td=v=>String(v||'').slice(0,10);
const KEY='dogson.close.public-candidate-history.v1';
const HOLIDAYS=new Set(['2026-10-09','2026-10-26','2026-12-25']);
const S={manifest:null,index:[],shards:new Map(),build:'',busy:false,seq:0,filter:'all',latest:'',error:'',visible:false};
const view=()=>$('.tab.active')?.dataset.view||'intraday';
const held=()=>{try{return window.RadarPortfolioStore?.list?.()||[]}catch{return[]}};
const allow=()=>window.DOGSON_CLOSE_DECISION_ALLOWED===true&&window.DOGSON_CLOSE_DATA_STATUS?.allowed===true&&!window.DOGSON_CLOSE_DATA_STATUS?.strictStale;
function dayPlus(date,num){const d=new Date(date+'T00:00:00Z');if(!Number.isFinite(d.getTime()))return'';for(let c=0;c<num;){d.setUTCDate(d.getUTCDate()+1);const a=d.toISOString().slice(0,10);if(d.getUTCDay()!==0&&d.getUTCDay()!==6&&!HOLIDAYS.has(a))c++}return d.toISOString().slice(0,10)}
function archiveRead(){try{const x=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(x)?x.filter(v=>v&&v.date&&Array.isArray(v.rows)).slice(-24):[]}catch{return[]}}
function archiveWrite(){if(!S.manifest||!S.index.length)return;const date=td(S.manifest.datasets?.decision_close_summary?.as_of);if(!date)return;try{const records=archiveRead().filter(x=>x.date!==date);records.push({date,rows:S.index.filter(x=>n(x.quote?.price)>0).slice(0,60).map(x=>({code:String(x.code),close:n(x.quote.price)}))});localStorage.setItem(KEY,JSON.stringify(records.sort((a,b)=>a.date.localeCompare(b.date)).slice(-24)))}catch{}}
function historyHtml(){const h=archiveRead();if(h.length<2)return '尚在累積本機盤後快照；至少兩個不同交易日才能開始對照。';
const byDate=new Map(h.map(x=>[x.date,new Map(x.rows.map(r=>[r.code,r.close]))]));
const out=[1,3,5,10].map(k=>{let up=0,seen=0,eligible=0;
for(const x of h){const y=byDate.get(dayPlus(x.date,k));if(!y)continue;for(const a of x.rows){eligible++;const z=y.get(a.code);if(n(z)==null||n(a.close)==null||a.close<=0)continue;seen++;if(z>a.close)up++}}
return k+'日 '+(seen?fmt(up/seen*100,0)+'% 上漲':'—')+'（'+seen+'/'+eligible+' 有對應收盤價）'}).join('｜');
return out+'。僅比較盤後收盤價變化，未觸發的買進不算成交；缺價、缺日期不補算，並非策略勝率。'}
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('資料讀取失敗 '+r.status);return r.json()}
function locate(){let box=$('#inukoCloseOps');if(!box){const anchor=$('#radarSummary');if(!anchor)return null;box=document.createElement('section');box.id='inukoCloseOps';box.className='close-ops';anchor.insertAdjacentElement('afterend',box)}return box}
function byScore(a,b){const as=n(a.scores?.swing_quality_score)||0,bs=n(b.scores?.swing_quality_score)||0,ap=n(a.scores?.entry_position_score)||0,bp=n(b.scores?.entry_position_score)||0;return bs+bp*.3-as-ap*.3}
function strongPeer(d){return (n(d.scores?.swing_quality_score)||0)>=65&&(n(d.scores?.entry_position_score)||0)>=55&&['SETUP','LAUNCH','PULLBACK_CONFIRMED','PULLBACK_TEST'].includes(d.lifecycle_stage)}
function peerCounts(){const m=new Map();S.index.filter(strongPeer).forEach(x=>{const key=String(x.primary_group||'').trim();if(key)m.set(key,(m.get(key)||0)+1)});return m}
function choose(){const pos=held(),heldCodes=new Set(pos.map(x=>String(x.code))),members=peerCounts();
const rows=[...S.index].sort(byScore);const pool=rows.filter(x=>!['FAILED','WEAKENING'].includes(x.lifecycle_stage)&&x.action_state!=='DATA_STALE');
const watch=pool.filter(x=>(n(x.scores?.swing_quality_score)||0)>=60&&(n(x.scores?.entry_position_score)||0)>=55).slice(0,25);
const included=[...watch,...pool.filter(x=>heldCodes.has(String(x.code)))].filter((x,i,a)=>a.findIndex(y=>String(y.code)===String(x.code))===i);
return included.map(x=>{const shard=S.shards.get(String(x.code)),e=shard?.evidence||{},d=shard?.decision||x;
const price=n(d.quote?.price??x.quote?.price),group=String(x.primary_group||''),peers=members.get(group)||0;
const readyChip=e.foreign_3buy===true&&e.sbl_3down===true&&[e.foreign_date,e.sbl_date].every(v=>td(v)===td(S.manifest.datasets?.decision_close_summary?.as_of));
const validLiq=n(e.avg_turnover20)>=30000000;
const overheated=(n(e.dist20)!=null&&e.dist20>8)||['DO_NOT_CHASE','EXIT_PRIORITY','REDUCE_WATCH'].includes(d.action_state)||['末端過熱／不追'].includes(d.ignition_stage)||d.no_chase===true;
const zones=(shard?.zones||[]).filter(z=>z.build_id===S.build&&z.trade_date===td(S.manifest.datasets?.decision_close_summary?.as_of)&&z.structure_state!=='INVALID');
const support=zones.filter(z=>z.side==='SUPPORT'&&n(z.low)!=null&&n(z.high)!=null&&price!=null&&z.low<=price).sort((a,b)=>b.high-a.high)[0]||null;
const resistance=zones.filter(z=>z.side==='RESISTANCE'&&n(z.high)!=null&&price!=null&&z.high>=price).sort((a,b)=>a.low-b.low)[0]||null;
const risk=price!=null&&support&&price>support.low?price-support.low:null;
const reward=price!=null&&resistance?resistance.low-price:null;
const rr=risk!=null&&risk>0&&reward!=null&&reward>0?reward/risk:null;
const zoneFresh=!!support&&!!resistance&&[support,resistance].every(z=>['FRESH','FROZEN'].includes(String(z.freshness||'')));
const sourceOK=!!shard&&shard.build_id===S.build&&td(shard.as_of)===td(S.manifest.datasets?.decision_close_summary?.as_of)&&n(d.data_confidence)>=80;
const meets=readyChip&&peers>=3&&validLiq&&!overheated&&sourceOK;
const early=['SETUP','LAUNCH','PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(d.lifecycle_stage)&&!overheated&&(n(e.dist20)==null||e.dist20<=7);
return {x,d,e,price,group,peers,readyChip,validLiq,overheated,sourceOK,zoneFresh,support,resistance,rr,meets,early,held:heldCodes.has(String(x.code)),position:pos.find(q=>String(q.code)===String(x.code))||null}})}
function calcStatus(a){if(!allow())return ['歷史參考','資料未通過最新盤後驗證，禁止據此下單'];
if(!a.sourceOK)return ['證據不足','個股證據／信心未通過驗證'];
if(a.held&&(a.position?.reason_status==='INVALID'||a.position?.reason_status==='WEAKENING'))return ['持倉風險','原始持有理由已弱化或失效，先處理持股風險'];
if(a.overheated)return ['不追','過熱或 Engine 標示不追'];
if(a.rr!=null&&a.rr<1.5)return ['先不追','從收盤價到 R1 的報酬／S1 風險比不足 1.5'];
if(!a.zoneFresh)return ['等結構核對','支撐／壓力 Zone 尚未標示為新鮮，不提供可執行價'];
if(a.meets&&(n(a.d.scores?.entry_position_score)||0)>=65)return ['優先觀察','籌碼＋族群共振；等回測與量價確認'];
if(a.early)return ['提前觀察','早期結構成立，等待個股觸發條件'];
return ['觀察','條件尚未完整，不提前買進']}
function zoneText(z){return z?p(z.low)+'～'+p(z.high):'—'}
function subCard(a){const st=calcStatus(a),q=n(a.d.scores?.swing_quality_score),loc=n(a.d.scores?.entry_position_score),known=!!a.support&&!!a.resistance;
const chip=a.readyChip?'外資3買＋借券3減':'籌碼未達雙條件';
const peer=a.peers>=3?'同族群共振 '+a.peers+' 檔':'同族群符合結構 '+a.peers+' 檔';
const thesis=a.held?(a.position?.reason_status==='INVALID'?'❌ 理由失效':a.position?.reason_status==='WEAKENING'?'⚠️ 理由弱化':a.position?.reason_status==='VALID'?'✅ 理由成立':'❔ 理由待驗'):'尚未持有';
const priceTag=a.zoneFresh?'已核對':'結構新鮮度待核對';
return '<article class="close-ops-card"><button type="button" class="close-ops-open" data-closeops-code="'+esc(a.x.code)+'"><b>'+esc(a.x.code+' '+a.x.name)+'</b><span>'+esc(st[0])+' ›</span></button>'
+'<div class="close-ops-mini">'+esc(thesis)+'｜品質 '+fmt(q,0)+'・位置 '+fmt(loc,0)+'｜'+esc(chip)+'｜'+esc(peer)+'</div>'
+'<div class="close-ops-prices"><div><small>回踩防守 S1</small><b>'+esc(zoneText(a.support))+'</b></div><div><small>突破確認 R1</small><b>'+esc(zoneText(a.resistance))+'</b></div><div><small>失效參考（S1下緣）</small><b>'+esc(a.support?p(a.support.low):'—')+'</b></div><div><small>收盤到 R1 報酬／風險</small><b>'+esc(a.rr!=null?fmt(a.rr,2)+' 倍':'不具備計算條件')+'</b></div></div>'
+'<p class="close-ops-hint">'+esc(st[1])+'。'+(known?'回踩守住、突破後回測不破並有量價確認才重新評估。':'結構價位不完整，不設假停損。')+'｜'+priceTag+'，價格以 '+esc(td(S.manifest.datasets?.decision_close_summary?.as_of))+' 收盤快照為準。</p></article>'}
function filtersHtml(rows){const opt=[['all','綜合優先'],['early','提前卡位'],['chip','籌碼三共振'],['held','我的持股']];return opt.map(([k,label])=>'<button type="button" data-closeops-filter="'+k+'" class="'+(S.filter===k?'active':'')+'">'+label+' '+rows.filter(a=>k==='all'||(k==='early'&&a.early)||(k==='chip'&&a.meets)||(k==='held'&&a.held)).length+'</button>').join('')}
function render(){const box=locate();if(!box)return;box.hidden=view()!=='close'||$('#radarPanel')?.classList.contains('h60-screen-active');if(box.hidden)return;
if(S.busy&&!S.index.length){box.innerHTML='<div class="close-ops-head"><b>🧭 犬子明日作戰補強</b></div><p>正在檢查盤後證據…</p>';return}
if(S.error&&!S.index.length){box.innerHTML='<b>盤後補強資料未載入</b><p>'+esc(S.error)+'</p>';return}
const list=choose(), positions=held(),risk=positions.filter(x=>['INVALID','WEAKENING','UNVERIFIED'].includes(x.reason_status)).length;
const flags=[allow()?'同日盤後資料可用':'⛔ 盤後資料未過執行檢查',positions.length+' 檔持倉',risk+' 檔持倉理由需驗',list.filter(x=>x.meets).length+' 檔籌碼共振（掃描池內）'];
let filtered=list.filter(a=>S.filter==='all'||(S.filter==='early'&&a.early)||(S.filter==='chip'&&a.meets)||(S.filter==='held'&&a.held));filtered=filtered.sort((a,b)=>Number(b.held&&['INVALID','WEAKENING'].includes(b.position?.reason_status))-Number(a.held&&['INVALID','WEAKENING'].includes(a.position?.reason_status))||byScore(a.x,b.x));
const market=$('#afterhoursDecision .ahd-head b')?.textContent||'市場資訊請見上方';
const scope=positions.length?'<div class="close-ops-strategy">持股先核對原始進場理由、有效跌破條件與持倉集中風險；未驗證理由不視為安全續抱。</div>':'';
box.innerHTML='<div class="close-ops-head"><div><b>🧭 犬子明日作戰｜選股與價格二次核對</b><small>市場 '+esc(market)+' · 不改原排名與 Engine 分數</small></div><span>'+esc(td(S.manifest?.datasets?.decision_close_summary?.as_of)||'—')+'</span></div>'
+'<div class="close-ops-flags">'+flags.map(x=>'<span>'+esc(x)+'</span>').join('')+'</div>'+scope
+'<div class="close-ops-tabs">'+filtersHtml(list)+'</div><div class="close-ops-list">'+(filtered.length?filtered.slice(0,12).map(subCard).join(''):'<p class="close-ops-empty">目前沒有符合這組二次篩選條件的個股；不放寬門檻補名單。</p>')+'</div>'
+'<details class="close-ops-extra"><summary>📊 歷史候選校準與風險來源</summary><p>'+esc(historyHtml())+'</p><p>期貨外資部位、散戶多空比、PCR、波動率及美元／台幣尚無經驗證的同日資料介面，本版不虛填，也不納入持股建議。</p><p>籌碼三共振＝外資連3買＋借券連3減＋同族群至少3檔具有合格的波段結構；另需流動性、Zone 與報酬風險條件驗證。以上均為篩選觀察，非下單訊號。</p></details>';
}
async function load(){if(view()!=='close')return;if(S.busy)return;S.busy=true;const seq=++S.seq;render();
try{const m=await json('./data/current_manifest.json?closeops='+Date.now());if(!m.health?.validation_passed||!m.active_build_id)throw Error('Atomic Build 未通過驗證');
if(S.build!==m.active_build_id){S.shards.clear();S.index=[];S.build=m.active_build_id}
S.manifest=m;const key=m.datasets?.decision_close_index;if(!key?.url)throw Error('缺少盤後候選索引');
if(!S.index.length){const idx=await json(key.url);if(!Array.isArray(idx))throw Error('盤後索引格式不正確');S.index=idx.filter(d=>String(d.build_id||m.active_build_id)===m.active_build_id)}
const picked=[...S.index].sort(byScore).filter(x=>(n(x.scores?.swing_quality_score)||0)>=60&&(n(x.scores?.entry_position_score)||0)>=55).slice(0,25);
const pos=new Set(held().map(x=>String(x.code)));const all=[...picked,...S.index.filter(x=>pos.has(String(x.code)))].slice(0,75);
const selected=[...new Set(all.map(x=>String(x.code)))].filter(code=>!S.shards.has(code)).slice(0,35);
await Promise.all(selected.map(async code=>{try{const s=await json('./data/builds/'+encodeURIComponent(m.active_build_id)+'/stock-shards/close/'+encodeURIComponent(code)+'.json');if(s?.build_id===m.active_build_id&&s.view==='close'&&td(s.as_of)===td(m.datasets.decision_close_summary?.as_of))S.shards.set(code,s)}catch{}}));
if(seq===S.seq){archiveWrite();S.error=''}
}catch(err){if(seq===S.seq)S.error=String(err.message||err);console.warn('inuko close ops',err)}
finally{if(seq===S.seq){S.busy=false;render()}}}
let scheduled=0;
function schedule(){clearTimeout(scheduled);scheduled=setTimeout(()=>{if(view()==='close'){if(!S.manifest&&!S.busy)load();else render()}else{const b=$('#inukoCloseOps');if(b)b.hidden=true}},70)}
document.addEventListener('click',e=>{const filter=e.target.closest('[data-closeops-filter]');if(filter){S.filter=filter.dataset.closeopsFilter;render();return}const code=e.target.closest('[data-closeops-code]');if(code){e.preventDefault();document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:code.dataset.closeopsCode,source:'close-ops'}}))}});
document.addEventListener('radar:view-rendered',schedule);
document.addEventListener('radar:data-reloaded',()=>{S.manifest=null;S.index=[];S.shards.clear();S.build='';load()});
document.addEventListener('radar:portfolio-changed',schedule);
document.addEventListener('inuko:portfolio-account-changed',schedule);
document.addEventListener('radar:afterhours-refresh',schedule);
document.addEventListener('click',e=>{if(e.target.closest('.tab,#h60ModeBar'))setTimeout(schedule,70)});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&view()==='close')load()});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
})();
(()=>{
'use strict';
if(window.__INUKO_PORTFOLIO_PRIORITY_LADDER_V1__)return;
window.__INUKO_PORTFOLIO_PRIORITY_LADDER_V1__=true;
if(!/\/v2(?:\/|$)/.test(location.pathname))return;

const C={build:'',data:new Map(),timer:null,running:false};
const $=(s,r=document)=>r.querySelector(s);
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const pct=(v,d=1)=>n(v)==null?'—':`${Number(v)>0?'+':''}${Number(v).toFixed(d).replace(/\.0$/,'')}%`;
const active=()=>$('.tab.active')?.dataset?.view||'';
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function manifest(){const m=await json(`./data/current_manifest.json?ladder=${Date.now()}`);if(C.build!==m.active_build_id){C.build=m.active_build_id;C.data.clear()}return m}
async function ds(m,key){const meta=m.datasets?.[key];if(!meta)return null;const ck=`${m.active_build_id}:${key}`;if(C.data.has(ck))return C.data.get(ck);const x=await json(meta.url);C.data.set(ck,x);return x}
function byRank(zones,ids,rank){const set=new Set(ids||[]);return zones.find(z=>set.has(z.zone_id)&&z.rank===rank)||null}
function currentPrice(d,e){return n(d?.quote?.price)??n(e?.close)}
function distancePct(px,z){const c=n(z?.center)??((n(z?.low)!=null&&n(z?.high)!=null)?(n(z.low)+n(z.high))/2:null);return px!=null&&c!=null&&px!==0?(c-px)/px*100:null}
function near(px,z,band=3){const d=distancePct(px,z);return d!=null&&Math.abs(d)<=band}
function belowZone(px,z){return px!=null&&n(z?.low)!=null&&px<n(z.low)}
function aboveZone(px,z){return px!=null&&n(z?.high)!=null&&px>n(z.high)}
function chipRisk(e){let bad=0;const f3=n(e?.foreign_3d_net),sbl=n(e?.sbl_3change_pct),mg=n(e?.margin_3d_pct);if(f3!=null&&f3<0)bad++;if(sbl!=null&&sbl>5)bad++;if(mg!=null&&mg>5)bad++;return bad>=2||(f3!=null&&f3<0&&sbl!=null&&sbl>0)}
function relRisk(d,e,indexQuote){const stock=n(e?.day_change)??n(d?.quote?.day_change_pct);const bench=d?.market==='上櫃'?n(indexQuote?.otc?.change_pct):n(indexQuote?.taiex?.change_pct);return stock!=null&&bench!=null&&(stock-bench)<=-1}
function techRisk(px,e){const ma20=n(e?.ma20);return px!=null&&ma20!=null&&px<ma20}
function systemRisk(d){return ['FAILED','WEAKENING'].includes(d?.lifecycle_stage)||['EXIT_PRIORITY','REDUCE_WATCH'].includes(d?.action_state)}

const META={
  0:{label:'L0 安心持有',emoji:'🟢',tone:'l0'},
  1:{label:'L1 持續觀察',emoji:'🔵',tone:'l1'},
  2:{label:'L2 今日重點',emoji:'🟡',tone:'l2'},
  3:{label:'L3 準備動作',emoji:'🟠',tone:'l3'},
  4:{label:'L4 立即處理',emoji:'🔴',tone:'l4'},
};
function classify(p,d,e,zones,indexQuote){
  const px=currentPrice(d,e),s1=byRank(zones,d?.support_zone_ids,'S1'),r1=byRank(zones,d?.resistance_zone_ids,'R1');
  const reasonInvalid=p.reason_status==='INVALID',reasonWeak=p.reason_status==='WEAKENING';
  const failed=d?.lifecycle_stage==='FAILED'||d?.action_state==='EXIT_PRIORITY';
  const weakening=d?.lifecycle_stage==='WEAKENING'||d?.action_state==='REDUCE_WATCH';
  const nearS=near(px,s1,3),veryNearS=near(px,s1,1.5),nearR=near(px,r1,3),underS=belowZone(px,s1),overR=aboveZone(px,r1);
  const chip=chipRisk(e),rel=relRisk(d,e,indexQuote),tech=techRisk(px,e);
  const moderate=[nearS,nearR,chip,rel,tech].filter(Boolean).length;
  let level=0;
  if(reasonInvalid||failed)level=4;
  else if(underS||weakening||(reasonWeak&&nearS)||(veryNearS&&(chip||rel||tech)))level=3;
  else if(reasonWeak||moderate>=2||veryNearS||(overR&&d?.action_state==='ADD_ON_CONFIRM'))level=2;
  else if(moderate===1||systemRisk(d))level=1;
  const reasons=[];
  if(reasonInvalid)reasons.push('進場理由失效'); else if(reasonWeak)reasons.push('進場理由弱化');
  if(failed)reasons.push('結構失效'); else if(weakening)reasons.push('結構轉弱');
  if(underS)reasons.push('已跌到 S1 下方'); else if(nearS)reasons.push('接近支撐');
  if(nearR)reasons.push('接近壓力');
  if(chip)reasons.push('籌碼轉弱');
  if(rel)reasons.push('弱於大盤');
  if(tech)reasons.push('20MA 下方');
  if(!reasons.length)reasons.push('核心結構正常');
  let conclusion='✅ 續抱';
  if(level===4)conclusion='❌ 優先處理風險';
  else if(level===3)conclusion=underS||weakening?'⚠️ 等確認後減碼／退出':'⚠️ 準備執行條件';
  else if(level===2)conclusion='✅ 續抱，但今天要確認';
  else if(level===1)conclusion='✅ 續抱，收盤再看';
  let next='維持結構即可';
  let clear='結構持續正常 → 維持 L0';
  if(level===4){next='依既定失效規則處理，不攤平';clear='重新建立有效結構與持有理由後才降級';}
  else if(level===3){next=underS?'若收盤／連續K確認跌破＋反抽不過 → 升 L4':weakening?'若弱化持續且反抽站不回 → 升 L4':'觸發既定加減碼條件後執行';clear='站回關鍵結構且量價改善 → 降回 L1/L2';}
  else if(level===2){next=nearS?'S1 失守或弱勢加劇 → 升 L3':nearR?'壓力區確認突破／受阻 → 決定加碼或維持':'再出現一項風險訊號 → 升 L3';clear='離開關鍵價＋籌碼／相對強弱改善 → 降回 L1';}
  else if(level===1){next='若再出現第二項警訊或靠近關鍵價 → 升 L2';clear='單一警訊消失 → 降回 L0';}
  return{level,meta:META[level],reasons:reasons.slice(0,3),conclusion,next,clear,code:String(p.code),name:p.name||d?.name||''};
}
function style(){if($('#portfolioPriorityLadderStyle'))return;const s=document.createElement('style');s.id='portfolioPriorityLadderStyle';s.textContent=`
.inuko-priority-row.l4 .tag,.inuko-port-intel-title .tone.l4{color:#9b2f2a;background:#ffeceb}.inuko-priority-row.l3 .tag,.inuko-port-intel-title .tone.l3{color:#9a5614;background:#fff0df}.inuko-priority-row.l2 .tag,.inuko-port-intel-title .tone.l2{color:#86620f;background:#fff7d8}.inuko-priority-row.l1 .tag,.inuko-port-intel-title .tone.l1{color:#2c6077;background:#eaf5fb}.inuko-priority-row.l0 .tag,.inuko-port-intel-title .tone.l0{color:#276451;background:#edf8f3}.inuko-ladder-extra{display:grid;gap:5px;margin:0 0 8px;padding:8px 9px;border-radius:9px;background:var(--card);border:1px solid var(--line);font-size:.64rem;line-height:1.45}.inuko-ladder-extra b{color:var(--text)}.inuko-priority-empty{padding:10px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:.7rem;line-height:1.45}.inuko-priority-row .why strong{display:block;color:var(--text);font-size:.66rem;margin-bottom:1px}
`;document.head.appendChild(s)}
function decorateCard(x){const card=$(`.portfolio-card[data-portfolio-code="${CSS.escape(x.code)}"]`);if(!card)return;const intel=$('.inuko-port-intel-card',card);if(!intel)return;const title=$('.inuko-port-intel-title',intel),tone=$('.tone',title);if(tone){tone.className=`tone ${x.meta.tone}`;tone.textContent=`${x.meta.emoji} ${x.meta.label}`}
  $('.inuko-ladder-extra',intel)?.remove();
  const extra=document.createElement('div');extra.className='inuko-ladder-extra';extra.innerHTML=`<div><b>犬子結論：</b>${esc(x.conclusion)}</div><div><b>升級條件：</b>${esc(x.next)}</div><div><b>解除警報：</b>${esc(x.clear)}</div>`;title?.insertAdjacentElement('afterend',extra);
}
function renderSummary(models){const root=$('#inukoPortfolioIntel');if(!root)return;const head=$('.inuko-pintel-head b',root);if(head)head.textContent='今天最需要看｜L2–L4';const list=$('.inuko-priority',root);if(!list)return;const urgent=models.filter(x=>x.level>=2).sort((a,b)=>b.level-a.level||a.code.localeCompare(b.code)).slice(0,5);if(!urgent.length){list.innerHTML='<div class="inuko-priority-empty">目前沒有 L2 以上持股。今天不用全部盯盤；L0 安心持有，L1 收盤再看即可。</div>';return}list.innerHTML=urgent.map(x=>`<div class="inuko-priority-row ${x.meta.tone}"><span class="code">${esc(x.code)} ${esc(x.name)}</span><span class="why"><strong>${esc(x.conclusion)}</strong>${esc(x.reasons.join('・'))}</span><span class="tag">${esc(`${x.meta.emoji} ${x.meta.label}`)}</span></div>`).join('')}
async function run(){if(C.running||active()!=='portfolio')return;const store=window.RadarPortfolioStore;if(!store)return;const positions=store.list?.()||[];if(!positions.length)return;C.running=true;try{const m=await manifest();const[idx,detail,zones,evidence,indexQuote]=await Promise.all([ds(m,'decision_close_index'),ds(m,'decision_close_detail'),ds(m,'zone_close'),ds(m,'stock_detail_close'),ds(m,'index_quote')]);const imap=new Map((Array.isArray(idx)?idx:[]).map(x=>[String(x.code),x])),dmap=detail?.items||{},emap=evidence?.items||{},zs=Array.isArray(zones)?zones:[];const models=positions.map(p=>classify(p,imap.get(String(p.code))||dmap[String(p.code)]||null,emap[String(p.code)]||null,zs,indexQuote||null));models.forEach(decorateCard);renderSummary(models)}catch(err){console.warn('portfolio priority ladder',err)}finally{C.running=false}}
function schedule(ms=750){clearTimeout(C.timer);C.timer=setTimeout(run,ms)}
function boot(){style();schedule(1000);document.addEventListener('radar:portfolio-changed',()=>schedule(900));document.addEventListener('radar:view-rendered',()=>schedule(900));document.addEventListener('inuko:portfolio-synced',()=>schedule(900));document.addEventListener('click',e=>{if(e.target?.closest?.('.tab[data-view="portfolio"]'))schedule(1100)},true)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

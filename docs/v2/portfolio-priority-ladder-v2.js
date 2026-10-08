(()=>{
'use strict';
if(window.__INUKO_PORTFOLIO_PRIORITY_LADDER_V2__)return;
window.__INUKO_PORTFOLIO_PRIORITY_LADDER_V2__=true;
if(!/\/v2(?:\/|$)/.test(location.pathname))return;

const C={build:'',data:new Map(),timer:null,running:false};
const $=(s,r=document)=>r.querySelector(s);
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[m]));
const active=()=>$('.tab.active')?.dataset?.view||'';
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function manifest(){const m=await json(`./data/current_manifest.json?ladder2=${Date.now()}`);if(C.build!==m.active_build_id){C.build=m.active_build_id;C.data.clear()}return m}
async function ds(m,key){const meta=m.datasets?.[key];if(!meta)return null;const ck=`${m.active_build_id}:${key}`;if(C.data.has(ck))return C.data.get(ck);const x=await json(meta.url);C.data.set(ck,x);return x}
function byRank(zones,ids,rank){const set=new Set((ids||[]).map(String));return zones.find(z=>set.has(String(z?.zone_id||''))&&z.rank===rank)||null}
function currentPrice(d,e){return n(d?.quote?.price)??n(e?.close)}
function distancePct(px,z){const c=n(z?.center)??((n(z?.low)!=null&&n(z?.high)!=null)?(n(z.low)+n(z.high))/2:null);return px!=null&&c!=null&&px!==0?(c-px)/px*100:null}
function near(px,z,band=3){const d=distancePct(px,z);return d!=null&&Math.abs(d)<=band}
function belowZone(px,z){return px!=null&&n(z?.low)!=null&&px<n(z.low)}
function aboveZone(px,z){return px!=null&&n(z?.high)!=null&&px>n(z.high)}
function tick(p){const x=Math.abs(Number(p));if(x<10)return .01;if(x<50)return .05;if(x<100)return .1;if(x<500)return .5;if(x<1000)return 1;return 5}
function price(v){const x=n(v);if(x==null)return'—';const t=tick(x),y=Math.round((x+Number.EPSILON)/t)*t,d=t<.1?2:t<1?1:0;return y.toLocaleString('zh-TW',{maximumFractionDigits:d})}
function zoneRange(z){if(!z)return'';const lo=n(z.low),hi=n(z.high),c=n(z.center);if(lo==null&&hi==null&&c==null)return'';if(lo==null&&hi==null)return price(c);if(lo==null)return price(hi);if(hi==null)return price(lo);return Math.abs(lo-hi)<1e-9?price(c??lo):`${price(lo)}–${price(hi)}`}
function chipRisk(e){let bad=0;const f3=n(e?.foreign_3d_net),sbl=n(e?.sbl_3change_pct),mg=n(e?.margin_3d_pct);if(f3!=null&&f3<0)bad++;if(sbl!=null&&sbl>5)bad++;if(mg!=null&&mg>5)bad++;return bad>=2||(f3!=null&&f3<0&&sbl!=null&&sbl>0)}
function relRisk(d,e,indexQuote){const stock=n(e?.day_change)??n(d?.quote?.day_change_pct);const bench=d?.market==='上櫃'?n(indexQuote?.otc?.change_pct):n(indexQuote?.taiex?.change_pct);return stock!=null&&bench!=null&&(stock-bench)<=-1}
function techRisk(px,e){const ma20=n(e?.ma20);return px!=null&&ma20!=null&&px<ma20}
function systemRisk(d){return ['FAILED','WEAKENING'].includes(d?.lifecycle_stage)||['EXIT_PRIORITY','REDUCE_WATCH'].includes(d?.action_state)}
function fullDecision(code,imap,dmap){const light=imap.get(code)||null,full=dmap[code]||null;return light||full?{...(light||{}),...(full||{})}:null}

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
  // A held stock can be outside the discovery/ranking pool. Missing source
  // evidence is a verification priority, never proof that risk is L0.
  const coverageMissing=!d||px==null||(!e&&!s1&&!r1);
  if(reasonInvalid||failed)level=4;
  else if(coverageMissing)level=2;
  else if(underS||weakening||(reasonWeak&&nearS)||(veryNearS&&(chip||rel||tech)))level=3;
  else if(reasonWeak||moderate>=2||veryNearS||(overR&&d?.action_state==='ADD_ON_CONFIRM'))level=2;
  else if(moderate===1||systemRisk(d))level=1;
  const reasons=[];
  if(reasonInvalid)reasons.push('進場理由失效'); else if(reasonWeak)reasons.push('進場理由弱化');
  if(failed)reasons.push('結構失效'); else if(weakening)reasons.push('結構轉弱');
  if(underS)reasons.push('目前位於 S1 下方'); else if(nearS)reasons.push('接近支撐');
  if(nearR)reasons.push('接近壓力');
  if(chip)reasons.push('籌碼轉弱');
  if(rel)reasons.push('弱於大盤');
  if(tech)reasons.push('20MA 下方');
  if(coverageMissing)reasons.unshift('行情或結構資料不足，需補查；不是賣出訊號');
  if(!reasons.length)reasons.push('核心結構正常');
  return{level,meta:META[level],reasons:reasons.slice(0,4),code:String(p.code),name:p.name||d?.name||'',px,s1,r1,nearS,nearR,underS,overR,reasonInvalid,reasonWeak,failed,weakening,chip,rel,tech,coverageMissing};
}

function guide(x){
  const s1=zoneRange(x.s1),r1=zoneRange(x.r1),sLow=price(x.s1?.low),sHigh=price(x.s1?.high),support=s1?`S1 ${s1}`:'關鍵支撐／原持有結構',resistance=r1?`R1 ${r1}`:'上方壓力區';
  if(x.coverageMissing&&x.level!==4)return{headline:'🟡 持倉資料待補查',now:'已有實際持股，不能因為未進波段候選池就免健檢；目前資料不足，暫不給虛構的 L0、技術或停損價。',trigger:'補齊最新成交價、日K與支撐／壓力後，再判斷是否升降 L 級。',avoid:'不能把沒有即時行情當成安全，也不要依缺資料的分數追價或砍倉。',clear:'成功補齊並通過日期驗證後，重新計算完整持倉風控。'};
  if(x.level===4)return{
    headline:'🔴 執行風控，不再只觀察',
    now:'核心持有理由或結構已確認失效：依你原先設定的減碼／退出方案執行；若尚未處理完，先把風險降下來。',
    trigger:`若反抽仍站不回失效位／${support}，繼續執行既定風控；不是看到短彈就取消原本的失效判斷。`,
    avoid:'不要攤平、不要用新的理由替舊交易找藉口，也不要把一根反彈 K 當成結構修復。',
    clear:'只有重新建立有效結構、進場理由重新成立，且量價轉好後，才重新評估是否降級或建立新交易。'
  };
  if(x.level===3)return{
    headline:'🟠 暫停加碼，先把下一步準備好',
    now:x.underS?`目前價格已到 ${support} 下方，但單次跌破還不直接當 L4。先確認收盤／連續 K、反抽與量價。`:`先停止新增部位；把「若失守要減多少、在哪個條件執行」先定好，尚未確認失效前不用搶著砍。`,
    trigger:`若${s1?`有效跌破下緣 ${sLow}`:'核心支撐有效跌破'}，並出現「收盤或連續 K 確認＋反抽站不回＋量價轉弱」，才升 L4 並執行既定減碼／退出。`,
    avoid:`不要因單根下影刺破${s1?` ${sLow}`:'支撐'}就砍；不要在警戒狀態攤平，也不要跌破後情緒性追殺。`,
    clear:`重新站回${s1?` ${sHigh}／S1 上緣`:'關鍵結構'}，且量價、相對強弱同步改善，可先降回 L2；結構恢復穩定再回 L1。`
  };
  if(x.level===2)return{
    headline:'🟡 續抱，但今天要盯關鍵條件',
    now:`既有部位先續抱，暫停隨意加碼；今天優先看 ${support}${r1?`、${resistance}`:''}，再看相對大盤與量價是否改善。`,
    trigger:x.nearR?`若 ${resistance} 有效突破且回測守住，再評估加碼；若受阻後轉弱或風險訊號增加，升 L3。`:`若 ${support} 失守，或再增加一項明確弱化訊號，升 L3 準備風控；若結構轉強則維持續抱。`,
    avoid:'不要在關鍵價附近追價；不要還沒確認就先加碼或先砍，也不要只看單一籌碼日做決定。',
    clear:'離開風險區、關鍵結構守住，且籌碼／相對強弱至少一項改善，可降回 L1。'
  };
  if(x.level===1)return{
    headline:'🔵 續抱，收盤再檢查即可',
    now:'目前只有單一或輕度警訊，部位先不動；不用一直盯盤，以收盤結構是否維持為主。',
    trigger:`若再出現第二項警訊，或價格靠近 ${support}／${resistance}，升 L2；若警訊自行消失，不需要額外動作。`,
    avoid:'不要因一根黑 K、單一法人日或短暫相對弱勢就急著砍；也不要因「看起來便宜」直接攤平。',
    clear:'單一警訊消失、核心理由仍成立且結構正常，即可降回 L0。'
  };
  return{
    headline:'🟢 續抱為主，照原計畫走',
    now:'核心理由與結構正常，維持原持有策略即可；不需要為了盤中小波動頻繁操作。',
    trigger:`只有既定條件成立才動作：回測 ${support} 守住可續抱；${r1?`${resistance} 有效突破且回測不破才評估加碼。`:'出現新的有效突破結構後才評估加碼。'}`,
    avoid:'不要離支撐太遠追高加碼，也不要因正常震盪提早賣掉原本仍成立的部位。',
    clear:'維持 L0；若出現單一警訊升 L1，靠近關鍵價或多項風險同時出現再升 L2。'
  };
}

function style(){if($('#portfolioPriorityLadderStyleV2'))return;const s=document.createElement('style');s.id='portfolioPriorityLadderStyleV2';s.textContent=`
.inuko-priority-row.l4 .tag,.inuko-port-intel-title .tone.l4{color:#9b2f2a;background:#ffeceb}.inuko-priority-row.l3 .tag,.inuko-port-intel-title .tone.l3{color:#9a5614;background:#fff0df}.inuko-priority-row.l2 .tag,.inuko-port-intel-title .tone.l2{color:#86620f;background:#fff7d8}.inuko-priority-row.l1 .tag,.inuko-port-intel-title .tone.l1{color:#2c6077;background:#eaf5fb}.inuko-priority-row.l0 .tag,.inuko-port-intel-title .tone.l0{color:#276451;background:#edf8f3}
.inuko-port-intel-card{padding:14px!important;border-radius:15px!important}.inuko-port-intel-title{margin-bottom:10px!important}.inuko-port-intel-title b{font-size:1.02rem!important;line-height:1.3}.inuko-port-intel-title .tone{font-size:.78rem!important;line-height:1.2;padding:6px 10px!important}
.inuko-ladder-action{display:grid;gap:0;margin:0 0 12px;border:1px solid var(--line);border-radius:13px;background:var(--card);overflow:hidden}.inuko-ladder-head{padding:10px 12px;font-size:.96rem;font-weight:900;line-height:1.45;border-bottom:1px solid var(--line)}.inuko-action-row{display:grid;grid-template-columns:76px minmax(0,1fr);gap:9px;padding:9px 12px;border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent)}.inuko-action-row:last-child{border-bottom:0}.inuko-action-row .k{font-size:.76rem;font-weight:850;color:var(--muted);line-height:1.55}.inuko-action-row .v{font-size:.91rem;line-height:1.55;color:var(--text);font-weight:620}.inuko-action-row.now .k{color:#285f4f}.inuko-action-row.trigger .k{color:#815f18}.inuko-action-row.avoid .k{color:#914139}.inuko-action-row.clear .k{color:#2c6077}
.inuko-intel-grid{gap:9px!important}.inuko-intel-grid>div{padding:10px 11px!important;border-radius:11px!important}.inuko-intel-grid span{font-size:.75rem!important;line-height:1.35}.inuko-intel-grid b{margin-top:3px!important;font-size:.96rem!important;line-height:1.38!important}.inuko-intel-grid small{margin-top:4px!important;font-size:.79rem!important;line-height:1.5!important}.inuko-plan{margin-top:10px!important;padding:11px 12px!important;border-radius:11px!important;font-size:.86rem!important;line-height:1.6!important}.inuko-data-note{margin-top:9px!important;font-size:.74rem!important;line-height:1.55!important}.inuko-priority-row .why strong{display:block;color:var(--text);font-size:.78rem;margin-bottom:2px}.inuko-priority-row .why{font-size:.76rem!important;line-height:1.5!important}.inuko-priority-row .code{font-size:.84rem!important}.inuko-priority-row .tag{font-size:.7rem!important;padding:5px 8px!important}.inuko-priority-row[data-portfolio-jump]{width:100%;font:inherit;color:inherit;text-align:left;cursor:pointer;appearance:none}.inuko-priority-row[data-portfolio-jump]:focus-visible{outline:3px solid #26715a;outline-offset:3px}.portfolio-card.inuko-jump-target{outline:3px solid #dba132;outline-offset:3px;scroll-margin-top:145px}.inuko-priority-empty{padding:11px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:.8rem;line-height:1.55}
@media(max-width:520px){.inuko-port-intel-card{padding:13px!important}.inuko-action-row{grid-template-columns:68px minmax(0,1fr);gap:8px;padding:9px 10px}.inuko-action-row .k{font-size:.78rem}.inuko-action-row .v{font-size:.93rem;line-height:1.6}.inuko-intel-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.inuko-intel-grid>div:nth-child(1),.inuko-intel-grid>div:nth-child(2),.inuko-intel-grid>div:nth-child(5),.inuko-intel-grid>div:nth-child(6){grid-column:1/-1}.inuko-intel-grid b{font-size:1rem!important}.inuko-intel-grid small{font-size:.82rem!important}.inuko-plan{font-size:.9rem!important}.inuko-data-note{font-size:.76rem!important}}
`;document.head.appendChild(s)}

function decorateCard(x){const card=$(`.portfolio-card[data-portfolio-code="${CSS.escape(x.code)}"]`);if(!card)return;const intel=$('.inuko-port-intel-card',card);if(!intel)return;const title=$('.inuko-port-intel-title',intel),tone=$('.tone',title);if(tone){tone.className=`tone ${x.meta.tone}`;tone.textContent=`${x.meta.emoji} ${x.meta.label}`}
  $('.inuko-ladder-extra',intel)?.remove();$('.inuko-ladder-action',intel)?.remove();
  const g=guide(x),extra=document.createElement('div');extra.className='inuko-ladder-action';extra.innerHTML=`<div class="inuko-ladder-head">${esc(g.headline)}</div><div class="inuko-action-row now"><div class="k">現在怎麼做</div><div class="v">${esc(g.now)}</div></div><div class="inuko-action-row trigger"><div class="k">觸發後</div><div class="v">${esc(g.trigger)}</div></div><div class="inuko-action-row avoid"><div class="k">不要做</div><div class="v">${esc(g.avoid)}</div></div><div class="inuko-action-row clear"><div class="k">解除／降級</div><div class="v">${esc(g.clear)}</div></div>`;title?.insertAdjacentElement('afterend',extra);
}
function renderSummary(models){
  const root=$('#inukoPortfolioIntel');if(!root)return;
  const urgent=models.filter(x=>x.level>=2).sort((a,b)=>b.level-a.level||a.code.localeCompare(b.code));
  const head=$('.inuko-pintel-head b',root);
  if(head)head.textContent='今天最需要看｜L2–L4（共 '+urgent.length+' 檔）';
  const list=$('.inuko-priority',root);if(!list)return;
  if(!urgent.length){list.innerHTML='<div class="inuko-priority-empty">目前沒有 L2–L4 持股；L0 與 L1 仍留在下方逐檔健檢。</div>';return;}
  list.innerHTML=urgent.map(x=>{const g=guide(x);return `<button type="button" class="inuko-priority-row ${x.meta.tone}" data-portfolio-jump="${esc(x.code)}" aria-label="跳至 ${esc(x.code)} ${esc(x.name)} 持倉詳情"><span class="code">${esc(x.code)} ${esc(x.name)}</span><span class="why"><strong>${esc(g.headline)}</strong>${esc(x.reasons.join('・'))}</span><span class="tag">${esc(`${x.meta.emoji} ${x.meta.label}`)}</span></button>`}).join('');
}
async function run(){if(C.running||active()!=='portfolio')return;const store=window.RadarPortfolioStore;if(!store)return;const positions=store.list?.()||[];if(!positions.length)return;C.running=true;try{const m=await manifest();const[idx,detail,zones,evidence,indexQuote]=await Promise.all([ds(m,'decision_close_index'),ds(m,'decision_close_detail'),ds(m,'zone_close'),ds(m,'stock_detail_close'),ds(m,'index_quote')]);const imap=new Map((Array.isArray(idx)?idx:[]).map(x=>[String(x.code),x])),dmap=detail?.items||{},emap=evidence?.items||{},zs=Array.isArray(zones)?zones:[];const models=positions.map(p=>{const code=String(p.code),d=fullDecision(code,imap,dmap);return classify(p,d,emap[code]||null,zs,indexQuote||null)});models.forEach(decorateCard);renderSummary(models)}catch(err){console.warn('portfolio priority ladder v2',err)}finally{C.running=false}}
function schedule(ms=650){clearTimeout(C.timer);C.timer=setTimeout(run,ms)}
function boot(){style();schedule(950);document.addEventListener('radar:portfolio-changed',()=>schedule(800));document.addEventListener('radar:view-rendered',()=>schedule(800));document.addEventListener('inuko:portfolio-synced',()=>schedule(800));document.addEventListener('click',e=>{const jump=e.target.closest?.('[data-portfolio-jump]');if(jump){const code=String(jump.dataset.portfolioJump||'');const card=[...document.querySelectorAll('#portfolioCards .portfolio-card[data-portfolio-code]')].find(el=>el.dataset.portfolioCode===code);if(card){e.preventDefault();card.scrollIntoView({behavior:'smooth',block:'start'});card.classList.add('inuko-jump-target');setTimeout(()=>card.classList.remove('inuko-jump-target'),1900)}return;}if(e.target?.closest?.('.tab[data-view="portfolio"]'))schedule(1000)},true)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

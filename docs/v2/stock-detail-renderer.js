const SDR={build:null,manifest:null,cache:new Map(),seq:0};

const SCFG={
  intraday:{detail:"decision_intraday_detail",zone:"zone_intraday",evidence:"stock_detail_intraday",label:"盤中波段"},
  close:{detail:"decision_close_detail",zone:"zone_close",evidence:"stock_detail_close",label:"盤後波段"},
  daytrade:{detail:"decision_daytrade_detail",zone:"zone_daytrade",evidence:"stock_detail_daytrade",label:"當沖"}
};
const SSTAGE={OBSERVE:"觀察",SETUP:"蓄勢待發",LAUNCH:"剛啟動",TREND:"趨勢持有",PULLBACK_TEST:"回踩觀察",PULLBACK_CONFIRMED:"回踩承接",WEAKENING:"轉弱警戒",FAILED:"結構失效"};
const SACTION={WATCH:"觀察",WAIT_TRIGGER:"等觸發",SMALL_TEST:"小量試單候選",WAIT_PULLBACK:"等回踩",HOLD:"續抱",ADD_ON_CONFIRM:"確認後加碼候選",DO_NOT_CHASE:"過熱不追",REDUCE_WATCH:"減碼觀察",EXIT_PRIORITY:"優先出場",DATA_STALE:"資料失效"};
const SFRESH={LIVE:"即時",FRESH:"盤後定格",FROZEN:"收盤定格",STALE:"過期",UNKNOWN:"未知"};
const SRISK={OVERHEAT:"過熱",EVENT_RISK:"事件風險",LIQUIDITY_RISK:"流動性風險",MARKET_RISK:"市場風險",TRADING_RESTRICTION:"交易限制",DATA_QUALITY_RISK:"資料品質風險"};
const SSTATE={TESTING:"測試中",NEAR:"接近",ACTIVE:"有效結構",BROKEN:"已失效"};

const sview=()=>document.querySelector(".tab.active")?.dataset.view||"intraday";
const sesc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const sn=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const sf=(v,d=1)=>sn(v)==null?"—":Number(v).toLocaleString("zh-TW",{maximumFractionDigits:d});
const ssigned=(v,d=1,s="")=>sn(v)==null?"—":`${Number(v)>0?"+":""}${sf(v,d)}${s}`;
const slots=v=>sn(v)==null?"—":`${Number(v)>0?"+":""}${sf(Number(v)/1000,1)} 張`;

function stick(p){const x=Math.abs(Number(p));if(x<10)return .01;if(x<50)return .05;if(x<100)return .1;if(x<500)return .5;if(x<1000)return 1;return 5}
function stickValue(v){const n=sn(v);if(n==null)return null;const t=stick(n);return Math.round((n+Number.EPSILON)/t)*t}
function sp(v){const n=stickValue(v);if(n==null)return"—";const t=stick(n),d=t<.1?2:t<1?1:0;return Number(n).toLocaleString("zh-TW",{maximumFractionDigits:d})}
function srange(z){if(!z)return"—";return sn(z.low)===sn(z.high)?sp(z.center??z.low):`${sp(z.low)}–${sp(z.high)}`}

async function sjson(url){
  const r=await fetch(url,{cache:"no-store"});
  if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);
  return r.json();
}
async function smanifest(force=false){
  if(SDR.manifest&&!force)return SDR.manifest;
  const m=await sjson(`./data/current_manifest.json${force?`?t=${Date.now()}`:""}`);
  if(SDR.build&&SDR.build!==m.active_build_id)SDR.cache.clear();
  SDR.build=m.active_build_id;
  SDR.manifest=m;
  return m;
}
async function sset(m,key){
  const meta=m.datasets?.[key];
  if(!meta)return null;
  const ck=`${m.active_build_id}:${key}`;
  if(SDR.cache.has(ck))return SDR.cache.get(ck);
  const obj=await sjson(meta.url);
  if(obj?.build_id&&obj.build_id!==m.active_build_id)throw new Error(`${key} build_id 不一致`);
  SDR.cache.set(ck,obj);
  return obj;
}

function safeOpen(dialog){
  if(!dialog||dialog.open)return;
  try{dialog.showModal()}
  catch(err){
    dialog.setAttribute("open","");
    dialog.classList.add("detail-dialog-fallback");
    console.warn("detail dialog fallback",err);
  }
}
function loadingShell(code){
  const dialog=document.getElementById("detailDialog"),title=document.getElementById("detailTitle"),body=document.getElementById("detailBody");
  if(!dialog||!title||!body)return null;
  title.textContent=`${String(code||"").trim()} 個股詳情`;
  body.innerHTML='<div class="detail-loading"><b>讀取個股詳情…</b><p class="muted">先載入核心決策，再補支撐壓力與技術／籌碼證據。</p></div>';
  safeOpen(dialog);
  return {dialog,title,body};
}

function style(){
  if(document.getElementById("stockDetailRendererStyle"))return;
  const st=document.createElement("style");
  st.id="stockDetailRendererStyle";
  st.textContent=`
.detail-loading{padding:18px 4px}.detail-loading b{display:block;font-size:.95rem}.detail-loading p{margin:7px 0 0;line-height:1.5}
.sdr-context{font-size:.72rem;color:#708078;margin:0 0 7px}.sdr-quick{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:10px 0}.sdr-quick>div{padding:9px 7px;border-radius:10px;background:var(--soft);text-align:center}.sdr-quick span{display:block;font-size:.7rem;color:var(--muted)}.sdr-quick b{display:block;margin-top:3px;font-size:1rem}
.sdr-evidence{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}.sdr-evidence>div{padding:8px;background:var(--soft);border-radius:9px}.sdr-evidence span{display:block;color:var(--muted);font-size:.68rem}.sdr-evidence b{display:block;margin-top:2px;font-size:.84rem}.sdr-evidence small{display:block;margin-top:2px;color:var(--muted);font-size:.67rem}
.sdr-note{font-size:.72rem;color:var(--muted);line-height:1.45;margin-top:7px}.sdr-explain{margin:12px 0 10px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.sdr-explain summary{padding:10px 11px;cursor:pointer;font-weight:750;font-size:.86rem;list-style:none}.sdr-explain summary::-webkit-details-marker{display:none}.sdr-explain summary:after{content:'＋';float:right}.sdr-explain[open] summary:after{content:'－'}.sdr-explain-body{padding:0 10px 10px}.sdr-exp-card{padding:8px 9px;border-top:1px dashed var(--line)}.sdr-exp-card:first-child{border-top:0}.sdr-exp-head{display:flex;justify-content:space-between;gap:10px;font-size:.82rem}.sdr-exp-item{display:grid;grid-template-columns:36px 1fr;gap:3px 7px;padding-top:5px;font-size:.78rem}.sdr-exp-pts{font-weight:800}.sdr-exp-detail{grid-column:2;color:var(--muted);font-size:.7rem;line-height:1.35}
.sr2-grid{display:grid;gap:9px}.sr2-card{border:1px solid var(--line);border-radius:14px;padding:11px 12px;background:var(--card)}.sr2-card.support{border-left:4px solid var(--green)}.sr2-card.resistance{border-left:4px solid var(--red)}.sr2-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.sr2-name{font-size:.78rem;font-weight:850}.sr2-state{font-size:.66rem;padding:3px 7px;border-radius:999px;background:var(--soft);color:var(--muted)}.sr2-main{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end;margin:7px 0 4px}.sr2-price{font-size:1.45rem;font-weight:900}.sr2-distance{text-align:right;font-size:.78rem;font-weight:750}.sr2-band{font-size:.7rem;color:var(--muted)}.sr2-evidence{margin-top:7px;font-size:.72rem;line-height:1.45}.sr2-strength{margin-top:5px;font-size:.69rem;color:var(--muted)}.sr2-rule{margin-top:7px;padding-top:7px;border-top:1px dashed var(--line);font-size:.68rem;line-height:1.5;color:var(--muted)}
.sdr-extra-loading{margin:12px 0;padding:10px 11px;border-radius:10px;background:var(--soft);font-size:.72rem;color:var(--muted)}
.tech2-card,.chip2-card{margin-top:9px;border:1px solid var(--line);border-radius:12px;padding:10px 11px;background:var(--card)}.tech2-head,.chip2-head{display:flex;justify-content:space-between;gap:10px;align-items:baseline}.tech2-head b,.chip2-head b{font-size:.86rem}.tech2-head strong,.chip2-head strong{font-size:1rem}.tech2-summary,.chip2-summary{margin-top:3px;font-size:.75rem;line-height:1.45;color:var(--muted)}.tech2-meta,.chip2-meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.tech2-meta span,.chip2-meta span{font-size:.66rem;padding:3px 6px;border-radius:999px;background:var(--soft);color:var(--muted)}.tech2-card details,.chip2-card details{margin-top:7px;border-top:1px dashed var(--line);padding-top:6px}.tech2-card summary,.chip2-card summary{cursor:pointer;list-style:none;font-size:.72rem;font-weight:800;color:var(--muted)}.tech2-card summary::-webkit-details-marker,.chip2-card summary::-webkit-details-marker{display:none}.tech2-card summary:after,.chip2-card summary:after{content:'＋';float:right}.tech2-card details[open] summary:after,.chip2-card details[open] summary:after{content:'－'}.tech2-grid,.chip2-grid{display:grid;gap:5px;margin-top:6px}.tech2-row,.chip2-row{display:grid;grid-template-columns:76px 58px 1fr;gap:7px;align-items:start;font-size:.7rem;line-height:1.42}.tech2-row b,.chip2-row b{font-size:.7rem}.tech2-row strong,.chip2-row strong{text-align:right}.tech2-row span,.chip2-row span{color:var(--muted)}
@media(max-width:520px){.sdr-quick{grid-template-columns:repeat(3,1fr)}.sr2-price{font-size:1.3rem}}
`;
  document.head.appendChild(st);
}

function tile(label,value,sub=""){return `<div><span>${sesc(label)}</span><b>${sesc(value??"—")}</b>${sub?`<small>${sesc(sub)}</small>`:""}</div>`}
function hourlyConfirm(x){
  const h=x?.hourly60||x;
  if(!h||h.data_status!=="OK")return "60分資料待補";
  const cat=String(h.category60||"");
  if(cat==="EARLY")return "60分初升確認";
  if(cat==="PRE_CROSS")return "60分金叉前夕";
  if(["STABLE_CONT","ACCEL_CONT"].includes(cat))return "60分趨勢確認";
  if(h.dir20==="DOWN")return "60分短線修正";
  if(h.dir20==="UP"&&["UP","FLAT"].includes(h.dir60))return "60分偏多";
  return "60分中性";
}
function tech2Section(x){
  if(!x||sn(x.technical_score_v2)==null)return"";
  const score=sn(x.technical_score_v2),conf=sn(x.technical_confidence_v2),legacy=sn(x.technical_score_legacy),delta=sn(x.technical_score_delta),parts=x.technical_components_v2||{};
  const order=["trend","breakout","volume_price","momentum","relative","risk_quality"];
  const rows=order.map(k=>{const p=parts[k];if(!p)return"";return `<div class="tech2-row"><b>${sesc(p.label||k)}</b><strong>${sf(p.score,1)}/${sf(p.max,0)}</strong><span>${sesc(p.detail||"")}</span></div>`}).join("");
  const deltaText=legacy!=null&&delta!=null?`舊制 ${sf(legacy,1)}/50 → 新制 ${sf(score,1)}/50（${ssigned(delta,1)}）`:"";
  const sar=x.sar!=null?`SAR ${x.sar_state==="BULL"?"多":"空"} ${sp(x.sar)}`:"";
  const kd=x.kd_k!=null&&x.kd_d!=null?`KD ${sf(x.kd_k,0)}/${sf(x.kd_d,0)}`:"";
  const h60=hourlyConfirm(x);
  return `<div class="tech2-card"><div class="tech2-head"><b>犬子技術 2.0 · ${sesc(x.technical_verdict_v2||"")}</b><strong>${sf(score,1)}/50</strong></div><div class="tech2-summary">${sesc(x.technical_summary_v2||"技術結構待確認")}｜生命週期：${sesc(x.technical_lifecycle_v2||"—")}</div><div class="tech2-meta"><span>資料信心 ${sf(conf,0)}%</span><span>${sesc(h60)}（不計分）</span>${sar?`<span>${sesc(sar)}</span>`:""}${kd?`<span>${sesc(kd)}</span>`:""}${deltaText?`<span>${sesc(deltaText)}</span>`:""}</div><details><summary>查看 6 項技術結構</summary><div class="tech2-grid">${rows||'<div class="sdr-note">技術分項待補。</div>'}</div></details></div>`;
}
function chip2Section(x){
  if(!x||sn(x.chip_score_v2_raw)==null)return"";
  const raw=sn(x.chip_score_v2_raw),pts=sn(x.chip_score_v2),conf=sn(x.chip_confidence_v2),legacy=sn(x.chip_score_legacy),delta=sn(x.chip_score_delta),parts=x.chip_components_v2||{};
  const order=["foreign","trust","sbl","margin","consensus","price_chip","sector_inst"];
  const rows=order.map(k=>{const p=parts[k];if(!p)return"";return `<div class="chip2-row"><b>${sesc(p.label||k)}</b><strong>${sf(p.points,1)}/${sf(p.weight,0)}</strong><span>${sesc(p.detail||`子分 ${sf(p.score,0)}/100`)}</span></div>`}).join("");
  const dates=[["外資",x.foreign_date],["投信",x.trust_date],["借券",x.sbl_date],["融資",x.margin_date]].filter(([,d])=>d).map(([k,d])=>`${k} ${String(d).slice(5)}`).join("・");
  const deltaText=legacy!=null&&delta!=null?`舊制 ${sf(legacy,1)}/25 → 新制 ${sf(pts,1)}/25（${ssigned(delta,1)}）`:"";
  return `<div class="chip2-card"><div class="chip2-head"><b>犬子籌碼 2.0 · ${sesc(x.chip_verdict_v2||"")}</b><strong>${sf(raw,0)}/100</strong></div><div class="chip2-summary">${sesc(x.chip_summary_v2||"籌碼方向待確認")}｜折算盤後總分 ${sf(pts,1)}/25</div><div class="chip2-meta"><span>資料信心 ${sf(conf,0)}%</span>${dates?`<span>${sesc(dates)}</span>`:""}${deltaText?`<span>${sesc(deltaText)}</span>`:""}</div><details><summary>查看 7 項籌碼結構</summary><div class="chip2-grid">${rows||'<div class="sdr-note">籌碼分項待補。</div>'}</div></details></div>`;
}
function comp(d,kind,key){return(d.components?.[kind]?.items||[]).find(x=>x.key===key)||null}
function readiness(d){
  const a=d.action_state;
  if(["EXIT_PRIORITY","REDUCE_WATCH"].includes(a)||["FAILED","WEAKENING"].includes(d.lifecycle_stage))return"風險優先";
  if(d.opportunity_bucket==="NEXT_DAY_READY"||["SMALL_TEST","ADD_ON_CONFIRM"].includes(a))return"候選";
  if(d.opportunity_bucket==="BREAKOUT_WATCH"||a==="WAIT_TRIGGER")return"等觸發";
  if(d.opportunity_bucket==="PULLBACK_WATCH"||a==="WAIT_PULLBACK")return"等回踩";
  return"觀察";
}
function quick(view,d){
  const s=d.scores||{};
  if(view==="close")return `${tile("波段品質",sf(s.swing_quality_score))}${tile("進場位置",sf(s.entry_position_score))}${tile("明日準備度",readiness(d))}`;
  if(view==="intraday"){
    const liq=comp(d,"intraday","liquidity_risk"),lv=sn(liq?.contribution),chase=lv==null?"待補":lv>=8?"低":lv>=5?"中":"高";
    return `${tile("盤中動能",sf(s.intraday_momentum_score))}${tile("進場位置",sf(s.entry_position_score))}${tile("追價風險",chase)}`;
  }
  const ex=comp(d,"daytrade","execution_structure"),flow=comp(d,"daytrade","flow_volume");
  return `${tile("當沖分",sf(s.daytrade_score))}${tile("執行結構",ex?`${sf(ex.contribution)}/${sf(ex.contribution_max,0)}`:"待補")}${tile("量價推進",flow?`${sf(flow.contribution)}/${sf(flow.contribution_max,0)}`:"待補")}`;
}
function humanWhy(x){
  let s=String(x||"").trim();
  s=s.replace(/^20日突破$/,"突破20日高點").replace(/^3日突破$/,"突破近3日高點").replace(/^均線多頭$/,"短中期均線偏多");
  s=s.replace(/^量比\s*([\d.]+)x$/i,(_,v)=>`量能約平常 ${sf(v,1)} 倍`);
  s=s.replace(/^距20MA\s*([+-]?[\d.]+%)$/i,(_,v)=>`距20日線 ${v}`);
  return s;
}
function list(title,xs,empty){
  const items=[...new Set((xs||[]).filter(Boolean).map(humanWhy))];
  return `<div class="detail-block"><h3>${sesc(title)}</h3><div class="detail-list">${items.length?items.map(x=>`<span>${sesc(x)}</span>`).join(""):`<span class="muted">${sesc(empty)}</span>`}</div></div>`;
}
function hero(view,d){
  const risk=["EXIT_PRIORITY","REDUCE_WATCH"].includes(d.action_state)||["FAILED","WEAKENING"].includes(d.lifecycle_stage);
  if(view==="close"){
    const good=d.opportunity_bucket==="NEXT_DAY_READY"||["SMALL_TEST","ADD_ON_CONFIRM"].includes(d.action_state);
    return {tone:risk?"risk":good?"go":"wait",light:risk?"風險優先":good?"明日候選":"明日觀察",text:risk?"結構轉弱，先處理風險。":good?"盤後先規劃明天要確認的價位，開盤後再看即時量價。":"目前先列觀察，條件成立前不用追。"};
  }
  const live=d.session_phase==="LIVE"&&d.freshness==="LIVE";
  if(view==="daytrade"&&!live)return{tone:"wait",light:"不可執行",text:"當沖只在即時資料合格時有效；這份資料只供回看。"};
  if(view==="intraday"&&!live)return{tone:"wait",light:"收盤定格",text:"這是盤中最後快照，只供回看；下個交易日要重新確認。"};
  if(risk)return{tone:"risk",light:"風險優先",text:"目前結構轉弱，先處理風險。"};
  if(d.actionable)return{tone:"go",light:"可執行",text:"目前條件已同步，但仍要守住支撐與追價限制。"};
  return{tone:"wait",light:"先等待",text:"目前還差觸發條件，先看不要急著進。"};
}
function blockers(view,d,support,resistance){
  const out=(d.blockers||[]).filter(Boolean).filter(x=>!(/資料不是目前可執行快照/.test(String(x))&&view==="close"));
  if(view==="close"&&resistance)out.push(`明天先看 ${srange(resistance)} 能不能站穩；沒站穩就先當作還沒突破。`);
  if(view==="intraday"&&resistance)out.push(`上方 ${srange(resistance)} 是最近壓力，先突破再看回測是否守住。`);
  if(view==="daytrade"&&resistance)out.push(`當沖先看 ${sp(resistance.high)} 能不能帶量突破；沒有確認就不追。`);
  if(sn(d.scores?.entry_position_score)==null&&view!=="daytrade")out.push("進場位置尚未建立，暫時不把目前價位當成可追。");
  return[...new Set(out)].slice(0,4);
}
function upgrades(view,d,support,resistance){
  const out=(d.upgrade_conditions||[]).filter(Boolean);
  if(resistance)out.push(view==="close"?`明天若量能維持、股價站穩 ${sp(resistance.high)}，再視為突破確認。`:`放量站上 ${sp(resistance.high)}，並回測 ${srange(resistance)} 不破。`);
  if(support)out.push(`若先回測 ${srange(support)} 守住，之後量價重新轉強，再考慮升級。`);
  return[...new Set(out)].slice(0,4);
}
function risks(view,d,support,e){
  let out=[...(d.risk_overlays||[]),...(d.risk_flags||[]),...(e?.daytrade_risks||[])].filter(Boolean).map(x=>SRISK[x]||x);
  if(view==="close")out=out.filter(x=>x!=="資料品質風險");
  if(support)out.push(`支撐失效不看單一刺穿：連續兩根對應K收在 ${sp(support.low)} 下方，或跌破後反抽站不回且量價轉弱，再視為確認失守。`);
  return[...new Set(out)];
}

function rankOrder(z){return({S1:1,S2:2,R1:1,R2:2})[z?.rank]||9}
function zoneDistance(z,px){const d=sn(z?.distance_pct);if(d!=null)return d;const c=sn(z?.center),p=sn(px);return c!=null&&p>0?(c/p-1)*100:null}
function stars(z){const n=Math.max(0,Math.min(5,Math.round(sn(z?.strength)||0)));return `${"★".repeat(n)}${"☆".repeat(5-n)}`}
function defaultValidation(z){return z?.side==="SUPPORT"?"回測價格帶守住，重新站回上緣；量縮回測優先。":"有效站上壓力上緣，量價同步，之後回測不破才算確認。"}
function defaultInvalidation(z){return z?.side==="SUPPORT"?"不因單一刺穿判定失守；連續兩根對應K收在下緣下方，或跌破後反抽站不回且量價轉弱，才視為結構失效。":"突破後若快速跌回壓力帶下方且無法站回，視為假突破，恢復壓力角色。"}
function zoneCard(z,px){
  if(!z)return"";
  const support=z.side==="SUPPORT",rank=z.rank||(support?"S1":"R1"),label=z.label||(rank==="S1"?"近端支撐":rank==="S2"?"第二支撐":rank==="R1"?"第一壓力":"第二壓力"),dist=zoneDistance(z,px),ev=(z.evidence||[]).filter(Boolean),state=SSTATE[z.structure_state]||z.structure_state||"有效結構";
  return `<div class="sr2-card ${support?"support":"resistance"}"><div class="sr2-head"><span class="sr2-name">${support?"🛡️":"⚡"} ${sesc(label)} · ${sesc(rank)}</span><span class="sr2-state">${sesc(state)}</span></div><div class="sr2-main"><div><div class="sr2-price">${sp(z.center)}</div><div class="sr2-band">價格帶 ${srange(z)}</div></div><div class="sr2-distance">距現價<br>${ssigned(dist,1,"%")}</div></div><div class="sr2-evidence">${ev.length?sesc(ev.join("＋")):"結構來源待補"}</div><div class="sr2-strength">${stars(z)}${z.evidence_count!=null?` · ${sf(z.evidence_count,0)} 項共振`:""}</div><div class="sr2-rule"><b>確認：</b>${sesc(z.validation_condition||defaultValidation(z))}<br><b>${support?"失效":"假突破"}：</b>${sesc(z.invalidation_condition||defaultInvalidation(z))}</div></div>`;
}
function zoneSection(supports,resistances,px){
  const s=supports.map(z=>zoneCard(z,px)).join(""),r=resistances.map(z=>zoneCard(z,px)).join("");
  return `<div class="detail-block"><h3>支撐區｜S1 / S2</h3><div class="sr2-grid">${s||'<div class="sr2-empty">沒有可信支撐時不猜單一價位。</div>'}</div></div><div class="detail-block"><h3>壓力區｜R1 / R2</h3><div class="sr2-grid">${r||'<div class="sr2-empty">沒有可信壓力時不猜單一價位。</div>'}</div><div class="sdr-note">四層結構是規劃工具，不是買進指令；S2／R2 不額外灌分。</div></div>`;
}

function evidence(view,x){
  if(!x)return'<div class="detail-note warn">同一 Atomic Build 的個股證據尚未建立，已停止補猜。</div>';
  if(view==="close")return `<div class="sdr-evidence">${tile("收盤",sp(x.close),ssigned(x.day_change,2,"%"))}${tile("5 / 10 / 20MA",`${sf(x.ma5,2)} / ${sf(x.ma10,2)} / ${sf(x.ma20,2)}`,`距20日線 ${ssigned(x.dist20,1,"%")}`)}${tile("量比",`${sf(x.vol_x,2)}x`,`20日均量 ${sf(x.avg_volume20,0)}`)}${tile("RSI / MACD",`${sf(x.rsi,1)} / ${ssigned(x.macd_h,2)}`)}${tile("外資今日",slots(x.foreign_net_latest),x.foreign_streak!=null?`連續 ${Number(x.foreign_streak)>0?"+":""}${sf(x.foreign_streak,0)} 日`:(x.foreign_3buy?"外資連3買":"非連3買"))}${tile("外資3日占量",ssigned(x.foreign_3d_volume_pct,1,"%"),slots(x.foreign_3d_net))}${tile("借券3日",ssigned(x.sbl_3change_pct,1,"%"),x.sbl_3down?"借券下降":"未連續下降")}${tile("融資3日",ssigned(x.margin_3d_pct,1,"%"),x.margin_status||"")}${tile("族群",x.sector_score_label||x.industry_name||"官方產業代理",`強勢比 ${sf(x.sector_hot_ratio)}%`)}</div>${tech2Section(x)}${chip2Section(x)}`;
  const rel=x.relative_multiframe||{},mt=x.multi_timeframe||{};
  return `<div class="sdr-evidence">${tile("現價",sp(x.close),ssigned(x.day_change,2,"%"))}${tile("VWAP",sf(x.vwap,2),`距VWAP ${ssigned(x.vwap_dist,2,"%")}`)}${tile("15分 / 60分",`${ssigned(x.ret15,2,"%")} / ${ssigned(x.ret60,2,"%")}`)}${tile("量速",`${sf(x.pace,2)}x`,`振幅 ${sf(x.amplitude_pct,2)}%`)}${tile("區間位置",`${sf(x.range_position_pct,1)}%`,x.amplitude_regime||"")}${tile("買一 / 賣一",`${sp(x.quote_bid1)} / ${sp(x.quote_ask1)}`)}${tile("多時框",mt.label||"—",mt["60m"]?.label||"")}${tile("相對市場",rel.label||"—",rel.relative_pct?.day!=null?`日 ${ssigned(rel.relative_pct.day,2,"%")}`:"")}${tile("籌碼背景",x.chip_background||"—",`籌碼分 ${sf(x.chip_score)}`)}${tile("族群",x.sector_score_label||x.industry_name||"官方產業代理",`強勢比 ${sf(x.sector_hot_ratio)}%`)}</div>`;
}

function expPoints(x){const p=sn(x?.points);if(p==null)return"•";return `${p>0?"+":""}${Number.isInteger(p)?p:sf(p,1)}`}
function expCard(label,obj){
  if(!obj)return"";
  const items=(obj.items||[]).map(it=>`<div class="sdr-exp-item"><span class="sdr-exp-pts">${sesc(expPoints(it))}</span><span>${sesc(it.label||"")}</span>${it.detail?`<span class="sdr-exp-detail">${sesc(it.detail)}</span>`:""}</div>`).join("");
  return `<div class="sdr-exp-card"><div class="sdr-exp-head"><b>${sesc(label)}</b><strong>${sf(obj.score)}/${sf(obj.max,0)}</strong></div>${items||'<div class="sdr-note">此分項目前沒有可顯示的輸入證據。</div>'}</div>`;
}
function eitem(label,value,detail=""){
  if(value==null||value===""||value==="—")return null;
  return {points:null,label:String(label),detail:String(detail||value)};
}
function einclude(arr,item){if(item)arr.push(item);return arr}
function intradayItems(kind,e){
  if(!e)return[];
  const out=[],mt=e.multi_timeframe||{},rel=e.relative_multiframe||{},rday=rel.relative_pct?.day;
  if(kind==="price_structure"){
    einclude(out,eitem("多時框",mt.label,mt["60m"]?.label?`60分：${mt["60m"].label}`:""));
    einclude(out,eitem("結構來源",e.structure_source));
    if(sn(e.vwap_dist)!=null)einclude(out,eitem("距VWAP",ssigned(e.vwap_dist,2,"%")));
    const breakout=e.break3?"突破近3日高點":e.break12?"突破近12根高點":"尚未出現短線突破";
    einclude(out,eitem("突破狀態",breakout));
  }else if(kind==="flow_volume"){
    if(sn(e.pace)!=null)einclude(out,eitem("量速",`${sf(e.pace,2)}x`));
    if(sn(e.vol_x)!=null)einclude(out,eitem("量比",`${sf(e.vol_x,2)}x`));
    if(e.structure_volume_verified!==undefined)einclude(out,eitem("結構量確認",e.structure_volume_verified?"已確認":"未確認"));
    if(sn(e.amplitude_pct)!=null)einclude(out,eitem("當日振幅",`${sf(e.amplitude_pct,2)}%`));
  }else if(kind==="relative_strength"){
    einclude(out,eitem("相對市場",rel.label));
    if(sn(rday)!=null)einclude(out,eitem("日相對強弱",ssigned(rday,2,"%")));
    if(sn(e.ret15)!=null||sn(e.ret60)!=null)einclude(out,eitem("15分 / 60分",`${ssigned(e.ret15,2,"%")} / ${ssigned(e.ret60,2,"%")}`));
  }else if(kind==="sector"){
    einclude(out,eitem("族群",e.sector_group||e.industry_name));
    einclude(out,eitem("族群狀態",e.sector_score_label));
    if(sn(e.sector_hot_ratio)!=null)einclude(out,eitem("強勢比",`${sf(e.sector_hot_ratio,1)}%`));
    if(sn(e.sector_score)!=null)einclude(out,eitem("族群分",sf(e.sector_score,1)));
  }else if(kind==="liquidity_risk"){
    einclude(out,eitem("流動性",e.liquidity_level));
    if(sn(e.avg_turnover20_mn)!=null)einclude(out,eitem("20日均成交額",`${sf(e.avg_turnover20_mn,1)} 百萬`));
    if(sn(e.range_position_pct)!=null)einclude(out,eitem("區間位置",`${sf(e.range_position_pct,1)}%`));
    if(sn(e.amplitude_pct)!=null)einclude(out,eitem("振幅",`${sf(e.amplitude_pct,2)}%`));
  }
  return out;
}
function explain(view,d,e){
  if(view==="close"){
    const x=d.score_explanations||{},techCard=e?.technical_model_version?"":expCard("技術",x.technical),chipCard=e?.chip_model_version?"":expCard("籌碼",x.chip);
    const notes=[];if(e?.technical_model_version)notes.push("技術採犬子2.0：趨勢、型態、量價、動能、相對強弱、結構風險共50分；60分K只作確認，不重複計分。");if(e?.chip_model_version)notes.push("籌碼採犬子2.0：內部先算100分，再固定折算為盤後25分；資料信心獨立。");
    return `<details class="sdr-explain"><summary>評分依據｜為什麼是這個分數</summary><div class="sdr-explain-body"><div class="sdr-note">波段品質＝技術50＋籌碼25＋族群15＋流動性10；進場位置另計100。 ${sesc(notes.join(" "))}</div>${techCard}${chipCard}${expCard("族群",x.sector)}${expCard("流動性",x.liquidity)}${expCard("進場位置",x.entry_position)}<div class="sdr-note">分數代表條件同步程度，不代表上漲機率。</div></div></details>`;
  }
  if(view==="intraday"){
    const c=e?.intraday_components||{};
    return `<details class="sdr-explain"><summary>評分依據｜盤中動能怎麼來</summary><div class="sdr-explain-body"><div class="sdr-note">盤中動能100＝價格結構30＋量價動能25＋相對強弱15＋族群20＋流動性／追價風險10。下列為同一快照可驗證的 Engine 輸入證據；前端不重新配分。</div>${expCard("價格結構",{score:c.price_structure,max:30,items:intradayItems("price_structure",e)})}${expCard("量價動能",{score:c.flow_volume,max:25,items:intradayItems("flow_volume",e)})}${expCard("相對強弱",{score:c.relative_strength,max:15,items:intradayItems("relative_strength",e)})}${expCard("族群共振",{score:c.sector,max:20,items:intradayItems("sector",e)})}${expCard("流動性／追價風險",{score:c.liquidity_risk,max:10,items:intradayItems("liquidity_risk",e)})}</div></details>`;
  }
  const items=(d.components?.daytrade?.items||[]);
  return `<details class="sdr-explain"><summary>評分依據｜當沖分怎麼來</summary><div class="sdr-explain-body">${items.map(x=>`<div class="sdr-exp-card"><div class="sdr-exp-head"><b>${sesc(x.label||x.key||"分項")}</b><strong>${sf(x.contribution)}/${sf(x.contribution_max,0)}</strong></div></div>`).join("")||'<div class="sdr-note">當沖分項依據待補。</div>'}</div></details>`;
}

function missing(d,support,resistance,e){
  const xs=[...(d.missing_fields||[])];
  if(!support)xs.push("支撐區");if(!resistance)xs.push("壓力區");if(!e)xs.push("個股證據");
  return[...new Set(xs)];
}

function coreHtml(view,cfg,d){
  const h=hero(view,d);
  return `<div class="sdr-context">${sesc(cfg.label)}詳情 · ${sesc(d.opportunity_bucket||"—")} · 排名 #${d.opportunity_rank??"—"}</div><div class="detail-hero"><div><span class="badge stage">${sesc(SSTAGE[d.lifecycle_stage]||d.lifecycle_stage||"—")}</span><h2>${sesc(SACTION[d.action_state]||d.action_state||"—")}</h2><p>${sesc(h.text)}</p></div><div class="detail-light ${h.tone}">${sesc(h.light)}</div></div><div class="sdr-quick">${quick(view,d)}</div>${list("為什麼現在看它",d.why_now||[],"目前沒有足夠的新理由。")} ${list("現在卡在哪裡",blockers(view,d,null,null),"目前沒有額外卡點。")}<div class="sdr-extra-loading">核心決策已載入；正在補支撐壓力與技術／籌碼證據…</div>${explain(view,d,null)}`;
}
function fullHtml(view,cfg,d,zones,ep){
  const e=ep?.items?.[String(d.code)]||null,wanted=new Set([...(d.support_zone_ids||[]),...(d.resistance_zone_ids||[])]),mine=(Array.isArray(zones)?zones:[]).filter(z=>wanted.has(z.zone_id)),supports=mine.filter(z=>z.side==="SUPPORT").sort((a,b)=>rankOrder(a)-rankOrder(b)).slice(0,2),resistances=mine.filter(z=>z.side==="RESISTANCE").sort((a,b)=>rankOrder(a)-rankOrder(b)).slice(0,2),support=supports[0]||null,resistance=resistances[0]||null,px=sn(e?.close??d.quote?.price),h=hero(view,d),miss=missing(d,support,resistance,e);
  return `<div class="sdr-context">${sesc(cfg.label)}詳情 · ${sesc(d.opportunity_bucket||"—")} · 排名 #${d.opportunity_rank??"—"}</div><div class="detail-hero"><div><span class="badge stage">${sesc(SSTAGE[d.lifecycle_stage]||d.lifecycle_stage||"—")}</span><h2>${sesc(SACTION[d.action_state]||d.action_state||"—")}</h2><p>${sesc(h.text)}</p></div><div class="detail-light ${h.tone}">${sesc(h.light)}</div></div><div class="sdr-quick">${quick(view,d)}</div>${zoneSection(supports,resistances,px)}${list("為什麼現在看它",[...(d.why_now||[]),...(e?.stage_reason?[e.stage_reason]:[])],"目前沒有足夠的新理由。")} ${list("現在卡在哪裡",blockers(view,d,support,resistance),"目前沒有額外卡點。")} ${list(view==="close"?"明日升級條件":"升級條件",upgrades(view,d,support,resistance),"目前尚未形成可量化的升級條件。")} ${list("失效／風險條件",risks(view,d,support,e),"目前沒有額外風險旗標。")}<div class="detail-block"><h3>${view==="close"?"盤後技術／籌碼":view==="daytrade"?"即時執行證據":"即時量價／相對強弱"}</h3>${evidence(view,e)}</div>${explain(view,d,e)}<div class="detail-block"><h3>資料品質</h3><div class="quality-grid">${tile("Freshness",SFRESH[d.freshness]||d.freshness||"—")}${tile("資料信心",`${sf(d.data_confidence,0)}%`)}${tile("覆蓋率",`${sf(d.component_coverage,0)}%`)}${tile("排名",`#${d.opportunity_rank??"—"}`)}</div>${miss.length?`<div class="missing">仍待補：${miss.map(sesc).join("、")}</div>`:'<div class="detail-note ok">主要決策資料已齊。</div>'}</div><details class="engineering"><summary>資料時間與版本</summary><div>as_of：${sesc(d.as_of||"—")}<br>known_at：${sesc(d.known_at||"—")}<br>context：${sesc(d.decision_context_id||"—")}<br>build：${sesc(d.build_id||"—")}<br>Zone：support ${supports.length} / resistance ${resistances.length}</div></details>`;
}

async function openStock(code,forcedView){
  const view=forcedView||sview();
  if(view==="portfolio")return;
  const ui=loadingShell(code);
  if(!ui)return;
  const seq=++SDR.seq,cfg=SCFG[view]||SCFG.intraday;

  try{
    const m=await smanifest();
    if(seq!==SDR.seq)return;
    const detail=await sset(m,cfg.detail);
    if(seq!==SDR.seq)return;
    const d=detail?.items?.[String(code)];
    if(!d||d.build_id!==m.active_build_id){
      ui.body.innerHTML='<div class="detail-note warn">找不到同一 Atomic Build 的完整資料，已停止顯示避免混用。</div>';
      return;
    }

    ui.title.textContent=`${d.code} ${d.name}`;
    ui.body.innerHTML=coreHtml(view,cfg,d);
    document.dispatchEvent(new CustomEvent("radar:detail-core-rendered",{detail:{code:String(code),view,build:m.active_build_id}}));

    await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,24)));
    if(seq!==SDR.seq||!ui.dialog.open)return;

    const [zones,epRaw]=await Promise.all([
      sset(m,cfg.zone).catch(()=>[]),
      sset(m,cfg.evidence).catch(()=>null)
    ]);
    if(seq!==SDR.seq||!ui.dialog.open)return;
    const ep=epRaw?.build_id===m.active_build_id?epRaw:null;
    ui.body.innerHTML=fullHtml(view,cfg,d,zones,ep);
    document.dispatchEvent(new CustomEvent("radar:detail-rendered",{detail:{code:String(code),view,build:m.active_build_id}}));
  }catch(err){
    console.error("stock-detail-renderer",err);
    if(seq!==SDR.seq)return;
    ui.body.innerHTML='<div class="detail-note warn">個股詳情載入失敗。已保留目前頁面，不會用不同版本資料補猜；請稍後再試。</div>';
  }
}

document.addEventListener("radar:open-stock",e=>{
  const code=String(e.detail?.code||"").trim();
  if(code)openStock(code,e.detail?.view);
});
document.addEventListener("radar:data-reloaded",()=>{
  SDR.build=null;SDR.manifest=null;SDR.cache.clear();SDR.seq++;
});
document.addEventListener("close",e=>{if(e.target?.id==="detailDialog")SDR.seq++},true);

style();

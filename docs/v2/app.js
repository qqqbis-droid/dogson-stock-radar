const state={
  view:"intraday",closeMode:"swing",manifest:null,cache:{},visibleCount:15,quickFilter:"",
  filterStage:"",filterAction:"",filterPosition:"",filterSector:"",
  search:"",externalSearch:[],loading:false,searchTimer:null,
  livePollTimer:null,livePollBusy:false,lastAutoCheckAt:0
};

const NEXT_DAY_ELITE={qualityMin:75,positionMin:65,confidenceMin:80};

const missionConfig={
  intraday:{label:"🔎 找波段｜現在先盯誰",title:"盤中優先",summary:"decision_intraday_summary",index:"decision_intraday_index",detail:"decision_intraday_detail",scoreKey:"intraday_momentum_score",scoreLabel:"盤中動能",stats:"intraday"},
  close:{label:"🌙 盤後作戰｜明天先準備誰",title:"明日優先",summary:"decision_close_summary",index:"decision_close_index",detail:"decision_close_detail",scoreKey:"swing_quality_score",scoreLabel:"波段品質",stats:"close"},
  portfolio:{label:"💼 我的庫存｜先處理風險",title:"持倉注意力",summary:null,index:null,detail:null,scoreKey:"swing_quality_score",scoreLabel:"波段品質",stats:null},
  daytrade:{label:"🎯 當沖執行｜只做可執行訊號",title:"當沖候選",summary:"decision_daytrade_summary",index:"decision_daytrade_index",detail:"decision_daytrade_detail",scoreKey:"daytrade_score",scoreLabel:"當沖分",stats:"daytrade"}
};

const stageLabel={OBSERVE:"觀察",SETUP:"蓄勢待發",LAUNCH:"剛啟動",TREND:"趨勢持有",PULLBACK_TEST:"回踩觀察",PULLBACK_CONFIRMED:"回踩承接",WEAKENING:"轉弱警戒",FAILED:"結構失效"};
const actionLabel={WATCH:"觀察",WAIT_TRIGGER:"等觸發",SMALL_TEST:"小量試單候選",WAIT_PULLBACK:"等回踩",HOLD:"續抱",ADD_ON_CONFIRM:"確認後加碼候選",DO_NOT_CHASE:"過熱不追",REDUCE_WATCH:"減碼觀察",EXIT_PRIORITY:"優先出場",DATA_STALE:"資料失效"};
const freshnessLabel={LIVE:"即時",FRESH:"新鮮",FROZEN:"收盤定格",STALE:"過期",UNKNOWN:"未知"};
const ignitionStageLabel={"蓄勢":"蓄勢","剛點火":"剛點火","突破回踩":"突破回踩","已發動等回踩":"等回踩","末端過熱／不追":"過熱不追","觀察":"觀察"};
const bucketLabel={TRIGGER_READY:"觸發就緒",WAIT_TRIGGER:"等待觸發",TREND_MONITOR:"趨勢追蹤",WAIT_PULLBACK:"等待回踩",RESEARCH_ONLY:"研究觀察",NEXT_DAY_READY:"明日候選",BREAKOUT_WATCH:"突破觀察",PULLBACK_WATCH:"回踩觀察",TREND_QUALITY:"趨勢品質",RESEARCH:"研究觀察",RISK:"風險優先",ACTIONABLE_NOW:"可執行",NO_TRADE:"不交易",STALE:"資料失效"};

const quickFilterConfig={
  intraday:{title:"盤中雷達快篩",subtitle:"點一下快速縮小名單，可再搭配下方條件",items:[
    {key:"TRIGGER_READY",label:"觸發就緒",icon:"⚡",note:"條件已靠近執行",kind:"bucket",values:["TRIGGER_READY"],tone:"go"},
    {key:"WAIT_TRIGGER",label:"等待觸發",icon:"⏳",note:"差最後一個訊號",kind:"bucket",values:["WAIT_TRIGGER"],tone:"wait"},
    {key:"TREND_MONITOR",label:"趨勢追蹤",icon:"↗",note:"結構仍在延續",kind:"bucket",values:["TREND_MONITOR"],tone:"trend"},
    {key:"RISK",label:"風險",icon:"!",note:"先看風險訊號",kind:"bucket",values:["RISK"],tone:"risk"}
  ]},
  close:{title:"明日作戰快篩",subtitle:"明日候選依條件全數列入，不設檔數上限",items:[
    {key:"NEXT_DAY_READY",label:"明日候選",icon:"✦",note:"品質≥75・位置≥65・信心≥80",kind:"bucket",values:["NEXT_DAY_READY"],tone:"go"},
    {key:"LAUNCH",label:"剛啟動",icon:"↗",note:"結構剛轉強",kind:"stage",values:["LAUNCH"],tone:"trend"},
    {key:"PULLBACK",label:"回踩",icon:"↘",note:"等承接確認",kind:"stage",values:["PULLBACK_TEST","PULLBACK_CONFIRMED"],tone:"wait"},
    {key:"RISK",label:"風險",icon:"!",note:"明天先處理風險",kind:"bucket",values:["RISK"],tone:"risk"}
  ]},
  daytrade:{title:"當沖執行快篩",subtitle:"先分執行狀態，再搭配位置與族群",items:[
    {key:"ACTIONABLE_NOW",label:"可執行",icon:"◎",note:"條件同步較完整",kind:"bucket",values:["ACTIONABLE_NOW"],tone:"go"},
    {key:"WAIT_TRIGGER",label:"等待觸發",icon:"⏳",note:"尚未完成觸發",kind:"bucket",values:["WAIT_TRIGGER"],tone:"wait"},
    {key:"NO_TRADE",label:"不交易",icon:"—",note:"目前不符合執行",kind:"bucket",values:["NO_TRADE"],tone:"neutral"},
    {key:"STALE",label:"資料失效",icon:"!",note:"資料不足不執行",kind:"bucket",values:["STALE"],tone:"risk"}
  ]}
};
const ignitionQuickFilter={title:"🔥 點火雷達快篩",subtitle:"找還沒離起漲點太遠的蓄勢／剛點火，不把末端噴出當機會",items:[
  {key:"IGNITION",label:"剛點火",icon:"🔥",note:"突破＋量能＋共振同步",kind:"ignition_stage",values:["剛點火"],tone:"go"},
  {key:"SETUP",label:"蓄勢",icon:"⌛",note:"平台附近等待正式突破",kind:"ignition_stage",values:["蓄勢"],tone:"trend"},
  {key:"RETEST",label:"突破回踩",icon:"↘",note:"回測突破帶看承接",kind:"ignition_stage",values:["突破回踩"],tone:"wait"},
  {key:"WAIT_PULLBACK",label:"等回踩",icon:"↩",note:"已發動但位置不宜追",kind:"ignition_stage",values:["已發動等回踩"],tone:"wait"},
  {key:"OVERHEAT",label:"過熱不追",icon:"!",note:"Gate 已限制追價",kind:"ignition_stage",values:["末端過熱／不追"],tone:"risk"}
]};

const $=s=>document.querySelector(s);
const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const num=v=>v==null||v===''||Number.isNaN(Number(v))?null:Number(v);
const fmt=(v,d=1)=>num(v)==null?"—":Number(v).toLocaleString("zh-TW",{maximumFractionDigits:d});
const priceFmt=v=>num(v)==null?"—":Number(v).toLocaleString("zh-TW",{maximumFractionDigits:2});
const compact=v=>num(v)==null?"—":new Intl.NumberFormat("zh-TW",{notation:"compact",maximumFractionDigits:1}).format(Number(v));
const signedPct=v=>num(v)==null?"—":`${Number(v)>0?"+":""}${fmt(v,2)}%`;
const isIgnitionMode=()=>state.view==="close"&&state.closeMode==="ignition";

function fail(message){
  const b=$("#healthBanner");
  if(b){b.classList.remove("hidden");b.textContent=`資料契約錯誤：${message}`}
  throw new Error(message);
}
async function getJson(url){
  const r=await fetch(url,{cache:"no-store"});
  if(!r.ok)fail(`${url} HTTP ${r.status}`);
  return r.json();
}
function assertSameBuild(objOrList,buildId,name){
  const arr=Array.isArray(objOrList)?objOrList:[objOrList];
  for(const x of arr){if(x?.build_id&&x.build_id!==buildId)fail(`${name} build_id 不一致`)}
}
async function dataset(key){
  if(!key)return null;
  if(state.cache[key])return state.cache[key];
  const meta=state.manifest?.datasets?.[key];
  if(!meta)return null;
  const data=await getJson(meta.url);
  assertSameBuild(Array.isArray(data)?data:(data?.items?Object.values(data.items):data),state.manifest.active_build_id,key);
  state.cache[key]=data;
  return data;
}

function phaseLabel(p){return({PRE_OPEN:"盤前",LIVE:"盤中",CLOSE_FREEZE:"收盤定格",POST_CLOSE:"盤後",NEXT_DAY:"隔日準備"})[p]||p||"—"}
function actionTone(d){
  if(isIgnitionMode()){
    const st=String(d.ignition_stage||"");
    if(st==="末端過熱／不追")return"risk";
    if(["剛點火","突破回踩"].includes(st))return"go";
    if(["蓄勢","已發動等回踩"].includes(st))return"wait";
    return"neutral";
  }
  if(d.action_state==="DATA_STALE")return"stale";
  if(["EXIT_PRIORITY","REDUCE_WATCH"].includes(d.action_state)||["FAILED","WEAKENING"].includes(d.lifecycle_stage))return"risk";
  if(d.actionable)return"go";
  if(["WAIT_TRIGGER","WAIT_PULLBACK","DO_NOT_CHASE"].includes(d.action_state))return"wait";
  return"neutral";
}
function scoreFor(d){if(isIgnitionMode())return d.scores?.ignition_score;const cfg=missionConfig[state.view],s=d.scores||{};return s[cfg.scoreKey]}
function summaryRows(){const cfg=missionConfig[state.view];return cfg?.summary?(state.cache[cfg.summary]||[]):[]}
function missionPhase(){if(state.view==="close")return"CLOSE_FREEZE";if(state.view==="portfolio")return"POST_CLOSE";return summaryRows()[0]?.session_phase||state.manifest?.session_phase}
function missionDate(){const cfg=missionConfig[state.view],meta=cfg?.summary?state.manifest?.datasets?.[cfg.summary]:null;return String(meta?.as_of||state.manifest?.trade_date||"").slice(0,10)}
function missionTime(){const cfg=missionConfig[state.view],meta=cfg?.summary?state.manifest?.datasets?.[cfg.summary]:null;return meta?.as_of||null}
function missionKnownAt(){const cfg=missionConfig[state.view],meta=cfg?.summary?state.manifest?.datasets?.[cfg.summary]:null,row=summaryRows()[0]||null;return row?.known_at||meta?.known_at||null}
function stamp16(v){return String(v||"").replace("T"," ").slice(0,16)}
function displayFreshness(d){if(state.view==="close"&&["FRESH","FROZEN"].includes(d.freshness))return"盤後定格";return freshnessLabel[d.freshness]||d.freshness||"—"}
function humanReason(text){
  let s=String(text||"").trim();
  s=s.replace(/^20日突破$/,"突破20日高點").replace(/^3日突破$/,"突破近3日高點");
  s=s.replace(/^量比\s*([\d.]+)x$/i,(_,x)=>`量能約平常 ${fmt(x,1)} 倍`);
  s=s.replace(/^距20MA\s*([+-]?[\d.]+%)$/i,(_,x)=>`距20日線 ${x}`);
  s=s.replace(/^均線多頭$/,"短中期均線偏多");
  return s;
}
function humanBlock(text){return String(text||"").trim().replace(/Trigger/g,"觸發條件").replace(/風險 Gate/g,"風險條件")}

function quoteHtml(d){
  const q=d.quote||{},p=num(q.price),chg=num(q.day_change_pct),cls=chg==null?"flat":chg>0?"rise":chg<0?"fall":"flat";
  let vol="量資料待補";
  if(state.view!=="close"&&num(q.pace)!=null)vol=`量速 ${fmt(q.pace,1)}x`;
  else if(num(q.relative_volume)!=null)vol=`量比 ${fmt(q.relative_volume,2)}x`;
  else if(num(q.volume)!=null){const unit=q.volume_unit==="SHARES"?"股":q.volume_unit==="LOTS"?"張":"";vol=`量 ${compact(q.volume)}${unit}`}
  const turnover=num(q.turnover_value_twd)!=null?`<div class="quote-turnover">成交值 ${compact(q.turnover_value_twd)}元</div>`:"";
  return `<div class="quote-strip"><div class="quote-price">${priceFmt(p)}</div><div class="quote-change ${cls}">${signedPct(chg)}</div><div class="quote-volume">${esc(vol)}</div>${turnover}</div>`;
}
function rankText(d){if(isIgnitionMode())return "🔥 點火 #"+(d.ignition_rank??"—");return `${bucketLabel[d.opportunity_bucket]||"排序"} #${d.opportunity_rank??"—"}`}
function sectorDisplay(d){const primary=String(d?.primary_group||"").trim();if(primary)return primary;const industry=String(d?.industry||d?.industry_name||d?.official_industry||"").trim();return industry?`${industry}・官方產業代理`:"分類待補"}
function sectorFilterKey(d){return String(d?.primary_group||d?.industry||d?.industry_name||d?.official_industry||"").trim()}

function quickSpec(){return isIgnitionMode()?ignitionQuickFilter:(quickFilterConfig[state.view]||null)}
function activeQuickItem(){return quickSpec()?.items?.find(x=>x.key===state.quickFilter)||null}
function isNextDayElite(d){
  const s=d?.scores||{};
  return d?.opportunity_bucket==="NEXT_DAY_READY"
    && num(s.swing_quality_score)!=null&&num(s.swing_quality_score)>=NEXT_DAY_ELITE.qualityMin
    && num(s.entry_position_score)!=null&&num(s.entry_position_score)>=NEXT_DAY_ELITE.positionMin
    && num(d?.data_confidence)!=null&&num(d.data_confidence)>=NEXT_DAY_ELITE.confidenceMin
    && !["WEAKENING","FAILED"].includes(d?.lifecycle_stage)
    && !["DO_NOT_CHASE","REDUCE_WATCH","EXIT_PRIORITY","DATA_STALE"].includes(d?.action_state);
}
function quickMatch(d){
  const q=activeQuickItem();
  if(!q)return true;
  if(isIgnitionMode()&&q.kind==="ignition_stage")return q.values.includes(d.ignition_stage);
  if(state.view==="close"&&q.key==="NEXT_DAY_READY")return isNextDayElite(d);
  return q.kind==="stage"?q.values.includes(d.lifecycle_stage):q.values.includes(d.opportunity_bucket);
}
function applyQuickRows(rows){
  const q=activeQuickItem();
  if(!q)return rows;
  return rows.filter(quickMatch);
}
function quickValue(item,buckets,stages){
  if(isIgnitionMode()&&item.kind==="ignition_stage")return (rowsForView()||[]).filter(d=>item.values.includes(d.ignition_stage)).length;
  if(state.view==="close"&&item.key==="NEXT_DAY_READY")return (rowsForView()||[]).filter(isNextDayElite).length;
  const source=item.kind==="stage"?stages:buckets;
  return item.values.reduce((sum,key)=>sum+Number(source?.[key]||0),0);
}

const LIVE_POLL_MS=45000;
function isLiveAutoView(){return ["intraday","close","portfolio","daytrade"].includes(state.view)}
function manifestMissionMeta(manifest,view=state.view){const cfg=missionConfig[view];return cfg?.summary?manifest?.datasets?.[cfg.summary]:null}
function manifestMissionKey(manifest,view=state.view){const meta=manifestMissionMeta(manifest,view);return `${manifest?.active_build_id||""}|${meta?.as_of||""}`}
async function applyFreshManifest(manifest,{source="manual"}={}){
  if(manifest.schema_version!=="2.0.0"||!manifest.health?.validation_passed)throw new Error("最新資料未通過 Contract Gate");
  state.cache={};state.externalSearch=[];window.RadarUniverseSearch?.clear?.();
  state.manifest=manifest;
  showHealth();
  await loadView();
  if(hasDeepFilter()){
    const needDetail=["NEAR_SUPPORT","NEAR_RESISTANCE"].includes(state.filterPosition);
    await applyDeepFilter({needDetail});
  }
  document.dispatchEvent(new CustomEvent("radar:data-reloaded",{detail:{build:manifest.active_build_id,source}}));
}
async function checkLiveUpdate(){
  if(!isLiveAutoView()||document.hidden||state.loading||state.livePollBusy)return;
  state.livePollBusy=true;state.lastAutoCheckAt=Date.now();
  try{
    const r=await fetch(`./data/current_manifest.json?t=${Date.now()}`,{cache:"no-store"});
    if(!r.ok)return;
    const manifest=await r.json();
    if(manifest.schema_version!=="2.0.0"||!manifest.health?.validation_passed)return;
    const currentMeta=manifestMissionMeta(state.manifest),nextMeta=manifestMissionMeta(manifest);
    const currentAsOf=String(currentMeta?.as_of||""),nextAsOf=String(nextMeta?.as_of||"");
    if(currentAsOf&&nextAsOf&&nextAsOf<currentAsOf)return;
    if(manifestMissionKey(manifest)===manifestMissionKey(state.manifest))return;
    await applyFreshManifest(manifest,{source:"auto"});
  }catch(err){console.warn("live auto refresh",err)}finally{state.livePollBusy=false}
}
function startLiveAutoRefresh(){
  if(state.livePollTimer)clearInterval(state.livePollTimer);
  state.livePollTimer=setInterval(()=>checkLiveUpdate(),LIVE_POLL_MS);
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)checkLiveUpdate()});
  window.addEventListener("focus",()=>checkLiveUpdate());
}
async function boot(){
  const manifest=await getJson("./data/current_manifest.json");
  if(manifest.schema_version!=="2.0.0")fail("不支援的 schema major");
  if(!manifest.health?.validation_passed)fail("active build validation failed");
  state.manifest=manifest;
  showHealth();
  await loadView();
  startLiveAutoRefresh();
}
async function reloadRadar(){
  if(state.loading)return;
  state.loading=true;
  const btn=$("#refreshBtn");
  if(btn){btn.disabled=true;btn.textContent="更新中…"}
  try{
    const manifest=await getJson(`./data/current_manifest.json?t=${Date.now()}`);
    if(manifest.schema_version!=="2.0.0"||!manifest.health?.validation_passed)fail("最新資料未通過 Contract Gate");
    await applyFreshManifest(manifest,{source:"manual"});
  }finally{
    state.loading=false;
    if(btn){btn.disabled=false;btn.textContent="重新整理"}
  }
}
function showHealth(){const b=$("#healthBanner");if(!b)return;b.classList.add("hidden");b.textContent=""}

async function loadView(){
  state.visibleCount=15;
  const cfg=missionConfig[state.view];
  if(state.view!=="portfolio"){
    const jobs=[dataset(cfg.summary),dataset("radar_stats")];
    if(isIgnitionMode()&&cfg.index)jobs.push(dataset(cfg.index));
    await Promise.all(jobs);
  }
  renderAll();
  document.dispatchEvent(new CustomEvent("radar:view-rendered",{detail:{view:state.view,build:state.manifest?.active_build_id}}));
}
function renderAll(){
  const cfg=missionConfig[state.view],m=state.manifest,phase=missionPhase(),date=missionDate(),time=missionTime(),knownAt=missionKnownAt();
  const dataStamp=stamp16(time||date||"—"),knownStamp=stamp16(knownAt);
  const timing=state.view==="close"?("收盤資料 "+dataStamp+(knownStamp?" · 最後補齊 "+knownStamp:"")):("資料 "+dataStamp);
  let closeSwitch="";
  if(state.view==="close"){
    closeSwitch='<div class="close-mode-switch" aria-label="盤後雷達模式">'
      +'<button type="button" data-close-mode="swing" class="'+(state.closeMode==="swing"?"active":"")+'">穩健波段</button>'
      +'<button type="button" data-close-mode="ignition" class="ignite '+(state.closeMode==="ignition"?"active":"")+'">🔥 點火雷達</button>'
      +'</div>';
  }
  $("#mission").innerHTML="<div>"+esc(cfg.label)+"</div><span>"+esc(phaseLabel(phase))+" · "+esc(timing)+"</span>"+closeSwitch;
  $("#rankingTitle").textContent=isIgnitionMode()?"🔥 點火雷達｜找加速前段":cfg.title;
  $("#statusBox").innerHTML="<b>"+esc(date||"—")+"</b><br><span>"+esc(phaseLabel(phase))+"</span><br><small>"+(state.view==="close"&&knownStamp?("定格更新 "+esc(knownStamp)+" · "):"")+(m.health.validation_passed?"Contract ✓":"檢查失敗")+"</small>";
  renderRadarSummary();renderStageFilter();renderActionFilter();renderPositionFilter();renderSectorFilter();renderCards();
}

function renderRadarSummary(){
  const box=$("#radarSummary");
  if(!box)return;
  if(state.view==="portfolio"){box.innerHTML="";box.hidden=true;return}
  box.hidden=false;
  const cfg=missionConfig[state.view],spec=quickSpec(),s=state.cache.radar_stats?.missions?.[cfg.stats]||{},b=s.buckets||{},g=s.stages||{},active=activeQuickItem();
  if(!spec){box.innerHTML="";return}
  box.innerHTML=`<div class="quick-filter-head"><div><b>${esc(spec.title)}</b><span>${esc(spec.subtitle)}</span></div>${active?'<button type="button" class="quick-filter-clear" data-quick-filter-clear>清除快篩 ×</button>':'<span class="quick-filter-tip">點一下篩選</span>'}</div><div class="quick-filter-grid">${spec.items.map(item=>{const selected=state.quickFilter===item.key,value=quickValue(item,b,g);return `<button type="button" class="quick-filter-card ${esc(item.tone)}${selected?" active":""}" data-quick-filter="${esc(item.key)}" aria-pressed="${selected?"true":"false"}"><span class="quick-filter-title"><i>${esc(item.icon)}</i><b>${esc(item.label)}</b><em>${selected?"✓":""}</em></span><strong>${Number(value).toLocaleString("zh-TW")}</strong><small>${esc(item.note)}</small></button>`}).join("")}</div>`;
}
function renderStageFilter(){
  const el=$("#stageFilter");if(!el)return;const current=state.filterStage;
  if(isIgnitionMode()){
    el.innerHTML='<option value="">全部點火階段</option>'+Object.entries(ignitionStageLabel).map(([k,v])=>'<option value="'+esc(k)+'">'+esc(v)+'</option>').join("");
  }else{
    el.innerHTML=['<option value="">全部階段</option>'].concat(Object.entries(stageLabel).map(([k,v])=>'<option value="'+k+'">'+v+'</option>')).join("");
  }
  el.value=current;
}
function renderActionFilter(){
  const el=$("#actionFilter");if(!el)return;const current=state.filterAction;
  el.innerHTML=isIgnitionMode()
    ?'<option value="">全部點火狀態</option><option value="IGNITION_TEST">小量試單候選</option><option value="WAIT_BREAKOUT">等突破</option><option value="WAIT_PULLBACK">等回踩</option><option value="NO_CHASE">不追</option><option value="WATCH">觀察</option>'
    :'<option value="">全部狀態</option><option value="ACTIONABLE">可執行</option><option value="WAIT">等待</option><option value="NO_CHASE">不追</option><option value="RISK">風險優先</option><option value="STALE">資料失效</option>';
  el.value=current;
}
function renderPositionFilter(){
  const el=$("#positionFilter");if(!el)return;const current=state.filterPosition;
  el.innerHTML='<option value="">全部位置</option><option value="NEAR_SUPPORT">靠近支撐／回踩</option><option value="BREAKOUT">突破中</option><option value="NEAR_RESISTANCE">壓力偏近</option><option value="OVERHEAT">過熱不追</option>';
  el.value=current;
}
function renderSectorFilter(){
  const el=$("#sectorFilter");if(!el)return;
  const current=state.filterSector,cfg=missionConfig[state.view],rows=state.cache[cfg.index]||state.cache[cfg.summary]||[],groups=[...new Set(rows.map(sectorFilterKey).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"zh-Hant"));
  el.innerHTML='<option value="">全部族群／產業</option>'+groups.map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join("");
  el.value=groups.includes(current)?current:"";
  if(current&&!groups.includes(current))state.filterSector="";
}

async function ensureIndex(){
  const cfg=missionConfig[state.view];
  if(!cfg.index)return;
  if(!state.cache[cfg.index])await dataset(cfg.index);
  const detail=cfg.detail?state.cache[cfg.detail]:null;
  if(detail?.items){
    for(const row of state.cache[cfg.index]||[]){
      const full=detail.items[String(row.code)]||{};
      if(!row.industry)row.industry=full.industry||null;
      if(!row.primary_group)row.primary_group=full.primary_group||null;
      if(!row.secondary_groups)row.secondary_groups=full.secondary_groups||[];
      if(!row.theme_tags)row.theme_tags=full.theme_tags||[];
    }
  }
}
async function ensureDetail(){const cfg=missionConfig[state.view];if(cfg.detail&&!state.cache[cfg.detail])await dataset(cfg.detail)}
function rowsForView(){
  const cfg=missionConfig[state.view];if(state.view==="portfolio")return[];
  const rows=state.cache[cfg.index]||state.cache[cfg.summary]||[];
  if(!isIgnitionMode())return rows;
  return [...rows].sort((a,b)=>(num(b.scores?.ignition_score)??-1)-(num(a.scores?.ignition_score)??-1)||(num(b.ignition_confidence)??0)-(num(a.ignition_confidence)??0)||String(a.code).localeCompare(String(b.code)));
}
function hasDeepFilter(){return Boolean(state.search.trim()||state.quickFilter||state.filterStage||state.filterAction||state.filterPosition||state.filterSector)}
function hasNonSearchFilter(){return Boolean(state.quickFilter||state.filterStage||state.filterAction||state.filterPosition||state.filterSector)}
function fullIndexLoaded(){const cfg=missionConfig[state.view];return Boolean(cfg.index&&state.cache[cfg.index])}
function filterAction(d){
  if(!state.filterAction)return true;
  if(isIgnitionMode()){
    if(state.filterAction==="IGNITION_TEST")return d.ignition_action==="小量試單候選"||d.ignition_action==="等承接／小量試單";
    if(state.filterAction==="WAIT_BREAKOUT")return d.ignition_action==="等突破";
    if(state.filterAction==="WAIT_PULLBACK")return d.ignition_action==="等回踩"||d.ignition_action==="等承接／小量試單";
    if(state.filterAction==="NO_CHASE")return d.ignition_action==="不追";
    if(state.filterAction==="WATCH")return d.ignition_action==="觀察";
    return true;
  }
  if(state.filterAction==="ACTIONABLE")return d.actionable===true;
  if(state.filterAction==="WAIT")return["WAIT_TRIGGER","WAIT_PULLBACK"].includes(d.action_state);
  if(state.filterAction==="NO_CHASE")return d.action_state==="DO_NOT_CHASE";
  if(state.filterAction==="RISK")return["EXIT_PRIORITY","REDUCE_WATCH"].includes(d.action_state)||["FAILED","WEAKENING"].includes(d.lifecycle_stage);
  if(state.filterAction==="STALE")return d.action_state==="DATA_STALE";
  return true;
}
function positionMatch(d){
  const f=state.filterPosition;
  if(!f)return true;
  if(f==="BREAKOUT")return isIgnitionMode()?["剛點火","突破回踩"].includes(d.ignition_stage):(d.lifecycle_stage==="LAUNCH"||(d.why_now||[]).some(x=>/突破/.test(String(x))));
  if(f==="OVERHEAT")return isIgnitionMode()?d.ignition_stage==="末端過熱／不追":(d.action_state==="DO_NOT_CHASE"||(d.risk_overlays||[]).includes("OVERHEAT"));
  const cfg=missionConfig[state.view],detail=state.cache[cfg.detail]?.items?.[String(d.code)]||d,labels=(detail.score_explanations?.entry_position?.items||[]).map(x=>String(x.label||"")),texts=[...(detail.blockers||[]),...(detail.upgrade_conditions||[])].join(" ");
  if(f==="NEAR_SUPPORT")return labels.some(x=>/支撐/.test(x))||[ "突破回踩","蓄勢" ].includes(d.ignition_stage)||["PULLBACK_TEST","PULLBACK_CONFIRMED"].includes(d.lifecycle_stage)||d.action_state==="WAIT_PULLBACK";
  if(f==="NEAR_RESISTANCE")return labels.some(x=>/壓力/.test(x))||/壓力|突破/.test(texts);
  return true;
}
function emptyMessage(rows,external){
  if(hasDeepFilter()&&!external.length)return"目前沒有符合篩選條件的股票，換一個條件看看。";
  if(!rows.length&&!external.length)return"目前資料集中沒有候選；雷達會保留空結果，不會用假資料補滿。";
  return"目前沒有符合條件的股票。";
}
function outsideCard(x){
  return `<article class="card neutral outside-pool"><div class="card-top"><div class="identity"><span class="rank">全市場 · 未排名</span><div><span class="code">${esc(x.code)} ${esc(x.name)}</span><div class="muted">${esc(x.sector_group||x.industry_name||"分類待補")} · ${esc(x.market||"")}</div></div></div><span class="badge stage">未進排名池</span></div><div class="action-line neutral"><span>○</span><b>不產生執行分</b><small>全市場搜尋</small></div><div class="reason">${esc(x._outsideReason||"目前不在雷達排名池。")}</div></article>`;
}

function ignitionCardHtml(d,cfg){
  const s=d.scores||{},tone=actionTone(d),score=scoreFor(d),fresh=displayFreshness(d);
  const reason=(d.ignition_reasons||[]).slice(0,2).map(humanReason);
  const gate=(d.ignition_gate_flags||[])[0]||"";
  const stage=ignitionStageLabel[d.ignition_stage]||d.ignition_stage||"資料待補";
  const action=d.ignition_action||"點火資料待補";
  const confidence=d.ignition_confidence??d.data_confidence;
  const atr=num(d.ignition_breakout_distance_atr);
  const dist=atr!=null?(" · 距突破點 "+fmt(atr,1)+" ATR"):"";
  const dot=["小量試單候選","等承接／小量試單"].includes(action)?"●":"○";
  return '<article class="card '+tone+'" data-ignition="1" data-code="'+esc(d.code)+'" role="button" tabindex="0" aria-label="查看 '+esc(d.code)+" "+esc(d.name)+' 個股詳情">'
    +'<div class="card-top"><div class="identity"><span class="rank">'+esc(rankText(d))+'</span><div><span class="code">'+esc(d.code)+" "+esc(d.name)+'</span><div class="muted">'+esc(sectorDisplay(d))+'</div></div></div><span class="badge stage">'+esc(stage)+'</span></div>'
    +quoteHtml(d)
    +'<div class="action-line '+tone+'"><span>'+dot+'</span><b>'+esc(action)+'</b><small>'+esc(fresh)+'</small></div>'
    +'<div class="score-row"><div class="score"><span>點火分數</span><b>'+fmt(score)+'</b></div><div class="score"><span>進場位置</span><b>'+fmt(s.entry_position_score)+'</b></div><div class="score"><span>點火信心</span><b>'+fmt(confidence,0)+'<small>%</small></b></div></div>'
    +'<div class="reason">'+(reason.length?reason.map(esc).join("・"):"目前無新增點火理由")+esc(dist)+'</div>'
    +(gate?'<div class="blocker">Gate：'+esc(humanBlock(gate))+'</div>':"")
    +'</article>';
}
function renderCards(){
  if(state.view==="portfolio"){
    $("#countText").textContent="私人資料";
    $("#cards").innerHTML="";
    $("#loadMore").classList.add("hidden");
    return;
  }
  let rows=rowsForView();
  const originalCount=rows.length,q=state.search.trim().toLowerCase(),cfg=missionConfig[state.view],indexLoaded=fullIndexLoaded(),canLoadFull=Boolean(cfg.index&&state.manifest?.datasets?.[cfg.index]),activeQuick=activeQuickItem();
  if(q)rows=rows.filter(d=>String(d.code||"").toLowerCase().includes(q)||String(d.name||"").toLowerCase().includes(q));
  rows=applyQuickRows(rows);
  if(state.filterStage)rows=rows.filter(d=>isIgnitionMode()?d.ignition_stage===state.filterStage:d.lifecycle_stage===state.filterStage);
  if(state.filterSector)rows=rows.filter(d=>sectorFilterKey(d)===state.filterSector);
  rows=rows.filter(filterAction).filter(positionMatch);
  const showAllNextDay=state.view==="close"&&!isIgnitionMode()&&state.quickFilter==="NEXT_DAY_READY";
  const external=q&&!hasNonSearchFilter()?state.externalSearch:[],shown=showAllNextDay?rows:rows.slice(0,state.visibleCount),shownCount=shown.length+external.length,prefix=activeQuick?`${activeQuick.label} · `:"";
  $("#countText").textContent=!indexLoaded&&canLoadFull&&!hasDeepFilter()?`已顯示 ${shown.length} 檔`:`${prefix}${shownCount}/${rows.length+external.length} 檔`;

  const rankedHtml=shown.map(d=>{
    if(isIgnitionMode())return ignitionCardHtml(d,cfg);
    const s=d.scores||{},tone=actionTone(d),score=scoreFor(d),reason=(d.why_now||[]).slice(0,2).map(humanReason),block=(d.blockers||[])[0],fresh=displayFreshness(d);
    return `<article class="card ${tone}" data-code="${esc(d.code)}" role="button" tabindex="0" aria-label="查看 ${esc(d.code)} ${esc(d.name)} 個股詳情"><div class="card-top"><div class="identity"><span class="rank">${esc(rankText(d))}</span><div><span class="code">${esc(d.code)} ${esc(d.name)}</span><div class="muted">${esc(sectorDisplay(d))}</div></div></div><span class="badge stage">${esc(stageLabel[d.lifecycle_stage]||d.lifecycle_stage)}</span></div>${quoteHtml(d)}<div class="action-line ${tone}"><span>${d.actionable?"●":"○"}</span><b>${esc(actionLabel[d.action_state]||d.action_state||"—")}</b><small>${esc(fresh)}</small></div><div class="score-row"><div class="score"><span>${esc(cfg.scoreLabel)}</span><b>${fmt(score)}</b></div><div class="score"><span>進場位置</span><b>${fmt(s.entry_position_score)}</b></div><div class="score"><span>資料信心</span><b>${fmt(d.data_confidence,0)}<small>%</small></b></div></div><div class="reason">${reason.length?reason.map(esc).join("・"):"目前無新增理由"}</div>${block?`<div class="blocker">卡點：${esc(humanBlock(block))}</div>`:""}</article>`;
  }).join("");
  const outsideHtml=external.map(outsideCard).join("");
  $("#cards").innerHTML=(rankedHtml+outsideHtml)||`<div class="empty-state"><b>${esc(emptyMessage(rows,external))}</b><p>原始雷達池 ${originalCount} 檔；空結果會保留並說明，不會自動放寬成假訊號。</p></div>`;

  const loadMore=$("#loadMore");
  if(showAllNextDay){loadMore.classList.add("hidden")}
  else if(!indexLoaded&&canLoadFull&&!hasDeepFilter()){loadMore.classList.remove("hidden");loadMore.textContent="查看更多全部候選"}
  else{const hasMore=state.visibleCount<rows.length;loadMore.classList.toggle("hidden",!hasMore);loadMore.textContent="查看更多"}
}

async function applyDeepFilter({needDetail=false}={}){
  if(state.view==="portfolio")return;
  await ensureIndex();
  if(needDetail)await ensureDetail();
  if(state.search.trim().length>=2&&window.RadarUniverseSearch?.search){
    state.externalSearch=await window.RadarUniverseSearch.search(state.search,state.cache[missionConfig[state.view].index]||[]);
  }else state.externalSearch=[];
  state.visibleCount=15;
  renderSectorFilter();renderRadarSummary();renderCards();
}
function resetFilters(){
  state.search="";state.externalSearch=[];state.quickFilter="";state.filterStage="";state.filterAction="";state.filterPosition="";state.filterSector="";
  clearTimeout(state.searchTimer);
  for(const id of ["searchInput","stageFilter","actionFilter","positionFilter","sectorFilter"]){const el=$("#"+id);if(el)el.value=""}
}
function openCard(card){
  const code=String(card?.dataset?.code||"").trim();
  if(!code||state.view==="portfolio")return;
  document.dispatchEvent(new CustomEvent("radar:open-stock",{detail:{code,view:state.view}}));
}

document.addEventListener("click",async e=>{
  const closeMode=e.target.closest?.("[data-close-mode]");
  if(closeMode&&state.view==="close"){
    state.closeMode=closeMode.dataset.closeMode==="ignition"?"ignition":"swing";
    resetFilters();state.visibleCount=15;
    if(isIgnitionMode())await ensureIndex();
    renderAll();
    return;
  }
  const tab=e.target.closest?.(".tab");
  if(tab){state.view=tab.dataset.view;resetFilters();document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===tab));await loadView();if(isLiveAutoView())checkLiveUpdate();return}

  const quickClear=e.target.closest?.("[data-quick-filter-clear]");
  if(quickClear){state.quickFilter="";state.visibleCount=15;renderRadarSummary();renderCards();return}

  const quick=e.target.closest?.("[data-quick-filter]");
  if(quick){const key=quick.dataset.quickFilter;state.quickFilter=state.quickFilter===key?"":key;renderRadarSummary();if(state.quickFilter)await applyDeepFilter();else{state.visibleCount=15;renderCards()}return}

  const card=e.target.closest?.("#cards .card[data-code]");
  if(card){openCard(card);return}

  if(e.target.id==="detailClose"){const d=$("#detailDialog");if(d?.open)d.close();return}

  if(e.target.id==="loadMore"){
    const btn=e.target,cfg=missionConfig[state.view],wasLoaded=Boolean(cfg.index&&state.cache[cfg.index]);
    if(!wasLoaded){btn.disabled=true;btn.textContent="載入全部候選中…";try{await ensureIndex();renderSectorFilter()}finally{btn.disabled=false}renderCards()}
    else{state.visibleCount+=15;renderCards()}
    return;
  }
  if(e.target.id==="refreshBtn"){await reloadRadar();return}
});

document.addEventListener("keydown",e=>{
  if(e.key!=="Enter"&&e.key!==" ")return;
  const card=e.target.closest?.("#cards .card[data-code]");
  if(!card||e.target!==card)return;
  e.preventDefault();openCard(card);
});

$("#searchInput")?.addEventListener("input",e=>{
  state.search=e.target.value;
  clearTimeout(state.searchTimer);
  if(!state.search.trim()){state.externalSearch=[];renderCards();return}
  state.searchTimer=setTimeout(()=>applyDeepFilter().catch(console.error),220);
});
$("#stageFilter")?.addEventListener("change",async e=>{state.filterStage=e.target.value;if(state.filterStage)await applyDeepFilter();else renderCards()});
$("#actionFilter")?.addEventListener("change",async e=>{state.filterAction=e.target.value;if(state.filterAction)await applyDeepFilter();else renderCards()});
$("#positionFilter")?.addEventListener("change",async e=>{state.filterPosition=e.target.value;const need=["NEAR_SUPPORT","NEAR_RESISTANCE"].includes(state.filterPosition);if(state.filterPosition)await applyDeepFilter({needDetail:need});else renderCards()});
$("#sectorFilter")?.addEventListener("focus",async()=>{if(state.view!=="portfolio"){await ensureIndex();renderSectorFilter()}});
$("#sectorFilter")?.addEventListener("change",async e=>{state.filterSector=e.target.value;if(state.filterSector)await applyDeepFilter();else renderCards()});

boot().catch(err=>{
  console.error(err);
  const b=$("#healthBanner");
  if(b?.classList.contains("hidden")){b.classList.remove("hidden");b.textContent="資料載入失敗，已停止提供可執行狀態。"}
});

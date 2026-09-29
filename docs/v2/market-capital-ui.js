const contextConfig={
  intraday:{market:"market_intraday_context",capital:"capital_intraday_context",capitalTitle:"即時族群動能"},
  daytrade:{market:"market_intraday_context",capital:"capital_intraday_context",capitalTitle:"即時族群動能"},
  close:{market:"market_close_context",capital:"capital_close_context",capitalTitle:"法人資金流向"},
  portfolio:{market:"market_close_context",capital:"capital_close_context",capitalTitle:"法人資金背景"}
};
const marketNames={BROAD_RISK_ON:"全面偏多",SELECTIVE_RISK_ON:"選股偏多",NEUTRAL:"中性",DEFENSIVE:"防守",RISK_OFF:"風險關閉"};
const freshNames={LIVE:"即時",FRESH:"新鮮",FROZEN:"收盤定格",STALE:"過期",UNKNOWN:"未知"};
const phaseNames={PRE_OPEN:"盤前",LIVE:"盤中",CLOSE_FREEZE:"收盤定格",POST_CLOSE:"盤後",NEXT_DAY:"隔日準備"};
let patching=false,scheduled=null,lastBuild=null,cache={};
const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]));
const n=v=>v==null||Number.isNaN(Number(v))?null:Number(v);
const fmt=(v,d=1)=>n(v)==null?"—":Number(v).toFixed(d).replace(/\.0$/,'');
const signed=(v,d=1,suffix="")=>n(v)==null?"—":`${Number(v)>0?"+":""}${Number(v).toFixed(d)}${suffix}`;
const money=v=>n(v)==null?"—":`${Number(v)>0?"+":""}${Number(v).toFixed(1)}億`;
function activeView(){return document.querySelector(".tab.active")?.dataset?.view||"intraday"}
async function json(url){const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function manifest(){const m=await json(`./data/current_manifest.json?context=${Date.now()}`);if(lastBuild!==m.active_build_id){cache={};lastBuild=m.active_build_id}return m}
async function dataset(m,key){if(cache[key])return cache[key];const meta=m.datasets?.[key];if(!meta)throw new Error(`manifest 缺少 ${key}`);const obj=await json(meta.url);if(obj?.build_id&&obj.build_id!==m.active_build_id)throw new Error(`${key} build_id 不一致`);cache[key]=obj;return obj}
function component(c,key,max){const x=c?.[key]||{};return `<div><b>${esc(key==="taiex"?"加權":key==="otc"?"櫃買":key==="breadth"?"市場廣度":key==="funds"?"資金動能":key==="sector"?"族群擴散":"官方外資")}</b><span>${fmt(x.score)}/${fmt(x.max??max,0)}</span></div>`}
function renderMarket(view,m){
 const box=document.getElementById("marketSummary"),detail=document.getElementById("marketDetail");if(!box||!detail)return;
 const intra=m.context==="INTRADAY",metrics=m.metrics||{},components=m.components||{};
 const model=intra?"盤中即時15分：加權3＋櫃買3＋廣度3＋資金動能4＋族群擴散2":"盤後15分：加權5＋櫃買4＋廣度3＋官方外資3";
 box.innerHTML=`<div data-market-context="${esc(view)}"><div class="market-grid"><div class="metric"><span>市場環境</span><b>${esc(marketNames[m.market_regime]||m.market_regime||"—")}</b></div><div class="metric"><span>市場分</span><b>${fmt(m.market_score)}<small>/15</small></b></div><div class="metric"><span>資料信心</span><b>${fmt(m.market_confidence,0)}<small>%</small></b></div></div><div class="data-line"><span class="fresh ${String(m.freshness||"").toLowerCase()}">${esc(freshNames[m.freshness]||m.freshness||"—")}</span><span>${esc(model)}</span></div></div>`;
 const comps=intra?[component(components,"taiex",3),component(components,"otc",3),component(components,"breadth",3),component(components,"funds",4),component(components,"sector",2)]:[component(components,"taiex",5),component(components,"otc",4),component(components,"breadth",3),component(components,"foreign",3)];
 const metricText=intra?`上漲股成交額 ${fmt(metrics.turnover_up_pct)}%｜站VWAP成交額 ${fmt(metrics.above_vwap_turnover_pct)}%｜量速 ${fmt(metrics.weighted_pace,2)}x`:`外資今日 ${money(metrics.foreign_net_billion)}｜上市 ${money(metrics.foreign_twse_billion)}｜上櫃 ${money(metrics.foreign_tpex_billion)}｜5日 ${money(metrics.foreign_5d_billion)}`;
 detail.innerHTML=`<div data-market-detail-context="${esc(view)}"><div class="detail-grid">${comps.join("")}</div><div class="data-line"><span>${esc(metricText)}</span></div><div class="detail-grid"><div><b>資料時間</b><span>${esc(m.as_of||"—")}</span></div><div><b>狀態</b><span>${esc(phaseNames[m.session_phase]||m.session_phase||"—")}</span></div></div></div>`;
 const mission=document.querySelector("#mission span");if(mission)mission.textContent=`${phaseNames[m.session_phase]||m.session_phase||"—"} · 資料 ${(m.as_of||"—").replace("T"," ").slice(0,16)}`;
}
function periodMoney(v,need,days){return n(v)==null?`累積 ${Math.min(Number(days)||0,need)}/${need}日`:money(v)}
function renderCapital(view,c){
 const title=document.getElementById("capitalTitle"),box=document.getElementById("sectorList");if(!box)return;const cfg=contextConfig[view];if(title)title.textContent=cfg.capitalTitle;
 const rows=Array.isArray(c.rows)?c.rows:[];
 if(c.context==="INTRADAY"){
  const show=[...rows].filter(x=>n(x.heat)!=null).sort((a,b)=>(b.heat??-99)-(a.heat??-99)).slice(0,10);
  box.innerHTML=show.map(x=>`<div class="chip" data-capital-context="${esc(view)}"><b>${esc(x.primary_group)}</b><strong>熱度 ${signed(x.heat,1)}</strong><div>成交占比 ${fmt(x.turnover_share_pct)}% · Δ ${signed(x.share_change_pp,1,"pp")}</div><div>VWAP ${fmt(x.above_vwap_pct)}% · 廣度 ${fmt(x.up_pct)}% · 量速 ${fmt(x.pace,2)}x</div><div>${esc(x.state||"")}</div></div>`).join("")||'<span class="muted" data-capital-context="intraday">即時族群動能待補</span>';
 }else{
  const buys=rows.filter(x=>(n(x.today_amount_100m)||0)>0).sort((a,b)=>(b.today_amount_100m||0)-(a.today_amount_100m||0)).slice(0,5);
  const sells=rows.filter(x=>(n(x.today_amount_100m)||0)<0).sort((a,b)=>(a.today_amount_100m||0)-(b.today_amount_100m||0)).slice(0,5);
  const one=(x,dir)=>`<div class="chip" data-capital-context="${esc(view)}"><b>${dir==="in"?"🔴":"🟢"} ${esc(x.primary_group)}</b><strong>${money(x.today_amount_100m)}</strong><div>${esc(x.flow_text||"資金方向中性")} ${x.accelerating?"· 加速":""}</div><div>5日 ${periodMoney(x.net5_amount_100m,5,x.amount_history_days)} · 20日 ${periodMoney(x.net20_amount_100m,20,x.amount_history_days)}</div><div>今日 ${signed(x.today_lots,0,"張")} · 覆蓋 ${fmt(x.amount_coverage_pct,0)}%</div></div>`;
  box.innerHTML=[...buys.map(x=>one(x,"in")),...sells.map(x=>one(x,"out"))].join("")||'<span class="muted" data-capital-context="close">盤後法人資金資料待補</span>';
 }
}
async function renderContext(){
 if(patching)return;patching=true;
 try{const view=activeView(),cfg=contextConfig[view]||contextConfig.intraday,m=await manifest();const [market,capital]=await Promise.all([dataset(m,cfg.market),dataset(m,cfg.capital)]);renderMarket(view,market);renderCapital(view,capital)}
 catch(err){console.error("market/capital context patch",err)}finally{patching=false}
}
function needsPatch(){const view=activeView();return !document.querySelector(`#marketSummary [data-market-context="${view}"]`)||!document.querySelector(`#sectorList [data-capital-context="${view}"]`)}
function schedule(delay=0){clearTimeout(scheduled);scheduled=setTimeout(()=>{if(needsPatch())renderContext()},delay)}
const observer=new MutationObserver(()=>{if(!patching&&needsPatch())schedule(0)});
for(const id of ["marketSummary","sectorList"]){const el=document.getElementById(id);if(el)observer.observe(el,{childList:true,subtree:true})}
document.addEventListener("click",e=>{if(e.target.closest(".tab"))schedule(80);if(e.target.id==="refreshBtn")schedule(500);if(e.target.id==="marketToggle")schedule(20)});
schedule(40);setTimeout(()=>schedule(0),600);setTimeout(()=>schedule(0),1600);

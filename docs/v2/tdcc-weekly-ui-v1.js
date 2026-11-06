/* INUKO LAB: TDCC official ownership evidence in individual stock cards/details.
   Independent weekly official open data; no changes to scores, ranks or trade signals.
   No full-market leaderboard in the close view.
*/
(function(root){
"use strict";
const esc=x=>String(x==null?"":x).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=x=>x==null||!Number.isFinite(Number(x))?"—":Number(x).toLocaleString("zh-TW",{maximumFractionDigits:2});
const pp=x=>x==null||!Number.isFinite(x)?"—":(x>0?"+":"")+fmt(x)+" pp";
const pct=x=>x==null||!Number.isFinite(Number(x))?"—":fmt(x)+"%";
const validDate=x=>/^\d{4}-\d{2}-\d{2}$/.test(String(x||""));
function todayTW(d=new Date()){
 const parts=new Intl.DateTimeFormat("en-US",{timeZone:"Asia/Taipei",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(d);
 const get=k=>parts.find(p=>p.type===k)?.value||"";
 return get("year")+"-"+get("month")+"-"+get("day");
}
function normalizeCode(x){
 return String(x||"").trim().toUpperCase().replace(/\.(TW|TWO)$/,"");
}
function summarize(code,weekly){
 if(!Array.isArray(weekly)||!weekly.length)return null;
 const rows=weekly.filter(x=>validDate(x?.date)&&Number.isFinite(x?.big400)&&Number.isFinite(x?.big1000))
   .slice().sort((a,b)=>b.date.localeCompare(a.date));
 if(!rows.length)return null;
 const latest=rows[0],change=(n,key)=>rows.length>n?+(latest[key]-rows[n][key]).toFixed(3):null;
 const d1=change(1,"big400"),d4=change(4,"big400"),d8=change(8,"big400");
 const kilo4=change(4,"big1000");
 let label="週期不足，持續觀察";
 if(d4!=null){
   label=Math.abs(d4)>=20?"大幅變動，先核對原因":d4>0?"大戶持股比增加":d4<0?"大戶持股比下降":"大戶持股比持平";
 }
 return{code:normalizeCode(code),latest,rows,d1,d4,d8,kilo4,label,extreme:d4!=null&&Math.abs(d4)>=20};
}
function cardHtml(summary,week){
 if(!summary)return"";
 const x=summary,cls=x.d4==null?"":x.d4>0?"tdcc-positive":x.d4<0?"tdcc-negative":"";
 return '<div class="tdcc-card-inline" data-tdcc-evidence="1" aria-label="官方集保大戶持股週變化">'+
  '<div class="tdcc-card-title">🏦 集保大戶 <small>官方週次 '+esc(x.latest.date||week||"—")+'</small></div>'+
  '<div class="tdcc-card-values"><span>400張級以上 <b>'+pct(x.latest.big400)+'</b></span>'+
  '<span>較前4期 <b class="'+cls+'">'+pp(x.d4)+'</b></span></div>'+
  (x.extreme?'<small class="tdcc-card-warning">大幅變動，須核對公司行為</small>':"")+
  '</div>';
}
function trendSvg(x){
 const rows=x.rows.slice(0,9).reverse();
 if(rows.length<2)return '<p class="tdcc-explain">尚不足兩期歷史，暫無趨勢圖。</p>';
 const values=rows.map(r=>r.big400),min=Math.min(...values),max=Math.max(...values),spread=Math.max(0.4,max-min);
 const path=values.map((value,i)=>{
  const px=28+i*286/Math.max(1,values.length-1);
  const py=100-70*((value-min)/spread);
  return(i?"L":"M")+px.toFixed(1)+" "+py.toFixed(1);
 }).join(" ");
 return '<svg class="tdcc-detail-trend" viewBox="0 0 345 130" role="img" aria-label="400張級以上持股比歷史走勢圖">'+
  '<line x1="27" y1="103" x2="321" y2="103" stroke="currentColor" opacity=".18"/>'+
  '<path d="'+path+'" fill="none" stroke="#188663" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>'+
  '<text x="1" y="23" font-size="10" fill="currentColor">'+fmt(max)+'%</text>'+
  '<text x="1" y="104" font-size="10" fill="currentColor">'+fmt(min)+'%</text>'+
  '<text x="28" y="125" font-size="10" fill="currentColor">'+esc(rows[0].date.slice(5))+'</text>'+
  '<text x="271" y="125" font-size="10" fill="currentColor">'+esc(rows[rows.length-1].date.slice(5))+'</text></svg>';
}
function detailHtml(summary,options={}){
 const x=summary,week=options.week||x?.latest.date||"—";
 const intro='<section class="tdcc-in-stock" data-tdcc-detail="1"><div class="tdcc-in-stock-head">'+
   '<h3>🏦 集保大戶持股變化</h3><small>官方週次 '+esc(week)+'</small></div>';
 if(!x)return intro+'<p class="tdcc-explain">此檔目前未取得完整的集保持股級距資料，不能推論大戶集中趨勢。這不是每日券商分點買賣超。</p></section>';
 const warning=options.stale?'<p class="tdcc-uncertain">此週資料已超過兩週未更新，僅供歷史研究，請勿當成最新籌碼。</p>':"";
 const extreme=x.extreme?'<p class="tdcc-uncertain">近四期大戶持股比變化超過 20 個百分點，可能涉及新掛牌、股權或股本變動、持股級距重新分配，請先核對公司行為，不可直接判定為吸貨。</p>':"";
 const tiles=[
  ["400張級以上",pct(x.latest.big400)],
  ["1,000張級以上",pct(x.latest.big1000)],
  ["400張級 1期變動",pp(x.d1)],
  ["400張級 4期變動",pp(x.d4)],
  ["400張級 8期變動",pp(x.d8)],
  ["1,000張級 4期變動",pp(x.kilo4)]
 ].map(([k,v])=>'<div><small>'+esc(k)+'</small><b>'+esc(v)+'</b></div>').join("");
 const table=x.rows.slice(0,10).map(r=>'<tr><td>'+esc(r.date)+'</td><td>'+pct(r.big400)+'</td><td>'+pct(r.big1000)+'</td><td>'+fmt(r.large_holders)+'</td></tr>').join("");
 return intro+warning+'<div class="tdcc-stock-tiles">'+tiles+'</div>'+
  '<p class="tdcc-in-stock-verdict">'+esc(x.label)+'。'+
  '這是持股級距的週變化，不代表主力分點買賣或可直接進場。</p>'+extreme+
  '<details class="tdcc-stock-history"><summary>查看最近集保週次與持股比例走勢</summary>'+trendSvg(x)+
  '<div class="tdcc-stock-table-wrap"><table><thead><tr><th>週次</th><th>400張級+</th><th>1,000張級+</th><th>大額級距人數</th></tr></thead><tbody>'+table+'</tbody></table></div></details>'+
  '<p class="tdcc-explain">資料：<a href="https://opendata.tdcc.com.tw/getOD.ashx?id=1-5" target="_blank" rel="noopener noreferrer">TDCC 集保官方開放資料</a>。400張級以上是各級距合計，分期比較按實際發布週次，假期可能不等於精確28日；與每日分點主力集中度不同。未納入原選股分數。</p></section>';
}
const helpers={summarize,cardHtml,detailHtml,todayTW,normalizeCode};
if(typeof module==="object"&&module.exports)module.exports=helpers;
if(!root||!root.document)return;
if(root.__INUKO_TDCC_INDIVIDUAL_V2__)return;
root.__INUKO_TDCC_INDIVIDUAL_V2__=true;
const document=root.document;
let loaded=null,error="",fetching=null,lastFetch=0,currentDetailCode="",currentDetailView="";
function find(code){return summarize(code,loaded?.stocks?.[normalizeCode(code)])}
function sourceAge(){
 if(!validDate(loaded?.latest_week))return null;
 return Math.floor((Date.parse(todayTW()+"T00:00:00Z")-Date.parse(loaded.latest_week+"T00:00:00Z"))/86400000);
}
function cardAllowed(){
 // TDCC historical ownership evidence may be viewed in all mission cards,
 // while it must never be presented as a same-day or actionable live signal.
 return Boolean(document.querySelector("#cards .card[data-code]"));
}
function renderCards(){
 if(!cardAllowed())return;
 for(const card of document.querySelectorAll("#cards .card[data-code]")){
   card.querySelectorAll("[data-tdcc-evidence]").forEach(el=>el.remove());
   const code=normalizeCode(card.dataset.code);
   const x=find(code);
   if(!x)continue;
   const wrapper=document.createElement("div");
   wrapper.innerHTML=cardHtml(x,loaded?.latest_week);
   const node=wrapper.firstElementChild;
   if(node)card.appendChild(node);
 }
}
function renderDetail(code,view){
 if(!code||!["close","intraday","daytrade","portfolio"].includes(view||""))return;
 const dialog=document.getElementById("detailDialog"),body=document.getElementById("detailBody");
 if(!dialog?.open||!body||!currentDetailCode||normalizeCode(code)!==currentDetailCode)return;
 body.querySelectorAll("[data-tdcc-detail]").forEach(el=>el.remove());
 const x=find(code),wrap=document.createElement("div");
 if(!loaded&&fetching)wrap.innerHTML='<section class="tdcc-in-stock" data-tdcc-detail="1"><h3>🏦 集保大戶持股變化</h3><p class="tdcc-explain">正在載入官方每週集保資料…</p></section>';
 else if(!loaded)wrap.innerHTML='<section class="tdcc-in-stock" data-tdcc-detail="1"><h3>🏦 集保大戶持股變化</h3><p class="tdcc-explain">'+esc(error||"尚未取得官方集保週資料")+'；暫不提供大戶訊號。</p></section>';
 else wrap.innerHTML=detailHtml(x,{week:loaded.latest_week,stale:sourceAge()>14});
 const section=wrap.firstElementChild;
 if(!section)return;
 // Position next to the existing technical / chip evidence, not in a new dashboard.
 const destination=body.querySelector(".detail-block")||body.querySelector(".chip2-card")||null;
 if(destination)destination.insertAdjacentElement("beforebegin",section);
 else body.appendChild(section);
}
async function refresh(force=false){
 if(fetching)return fetching;
 if(!force&&loaded&&Date.now()-lastFetch<3600000)return loaded;
 fetching=(async()=>{
   try{
     const response=await fetch("./data/tdcc_weekly_concentration.json?individual_v=2&t="+Date.now(),{cache:"no-store"});
     if(!response.ok)throw Error("集保資料尚未成功發布（HTTP "+response.status+"）");
     const data=await response.json();
     if(data.schema!=="tdcc-weekly-ownership-v1"||!validDate(data.latest_week)||!data.stocks||Object.keys(data.stocks).length<800)
       throw Error("來源資料不符官方週資料格式");
     if(data.latest_week>todayTW())throw Error("官方來源日期晚於今天，拒絕使用");
     loaded=data;error="";lastFetch=Date.now();
   }catch(e){error=String(e.message||e);if(!loaded)lastFetch=0}
   finally{
     fetching=null;
     renderCards();
     if(currentDetailCode)renderDetail(currentDetailCode,currentDetailView);
   }
   return loaded;
 })();
 return fetching;
}
function onOpen(e){
 const code=normalizeCode(e.detail?.code),view=String(e.detail?.view||"close");
 if(!code)return;
 currentDetailCode=code;currentDetailView=view;
 void refresh();
}
function onDetail(e){
 const code=normalizeCode(e.detail?.code),view=String(e.detail?.view||"");
 if(!code||code!==currentDetailCode)return;
 currentDetailView=view||currentDetailView;
 renderDetail(code,currentDetailView);
}
function boot(){
 document.addEventListener("radar:cards-rendered",renderCards);
 document.addEventListener("radar:open-stock",onOpen);
 document.addEventListener("radar:detail-core-rendered",onDetail);
 document.addEventListener("radar:detail-rendered",onDetail);
 document.addEventListener("radar:view-rendered",()=>{renderCards();void refresh()});
 document.addEventListener("radar:data-reloaded",()=>{lastFetch=0;void refresh(true)});
 document.addEventListener("close",e=>{if(e.target?.id==="detailDialog"){currentDetailCode="";currentDetailView=""}},true);
 root.InukoTdccWeekly={status:()=>({latest_week:loaded?.latest_week||null,count:Object.keys(loaded?.stocks||{}).length,error}),refresh:()=>refresh(true),summary:code=>find(code)};
 void refresh();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})(typeof window!=="undefined"?window:null);

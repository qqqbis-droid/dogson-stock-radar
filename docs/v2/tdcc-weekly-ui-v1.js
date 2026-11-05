/* TDCC official open data weekly big-holder concentration: automatic, separate from branch data. */
(function(){
"use strict";
if(window.__INUKO_TDCC_WEEKLY_V1__)return;window.__INUKO_TDCC_WEEKLY_V1__=true;
let host=null,loaded=null,error="",loading=false,query="",kind="GAIN",openCode="",lastFetch=0;
const todayTW=()=>{const p=new Intl.DateTimeFormat("en-US",{timeZone:"Asia/Taipei",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());const v=k=>p.find(x=>x.type===k)?.value||"";return v("year")+"-"+v("month")+"-"+v("day")};
const esc=v=>String(v==null?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=v=>v==null||!Number.isFinite(v)?"—":Number(v).toLocaleString("zh-TW",{maximumFractionDigits:2});
const diff=v=>v==null?"—":(v>0?"+":"")+fmt(v)+" pp";
const visible=()=>Boolean(document.querySelector('.tab.active[data-view="close"]')&&!document.querySelector("#radarPanel")?.classList.contains("h60-screen-active"));
function summarize(code,weeks){
 if(!Array.isArray(weeks)||!weeks.length)return null;
 const a=weeks.slice().sort((x,y)=>y.date.localeCompare(x.date)),newest=a[0];
 const earlier=(n,key)=>a[n]&&Number.isFinite(a[n][key])?+(newest[key]-a[n][key]).toFixed(3):null;
 const one=earlier(1,"big400"),four=earlier(4,"big400"),eight=earlier(8,"big400");
 const label=four==null?"歷史週次不足":four>0&&one!=null&&one>0?"大戶集中延續":four>0?"四週集中增加":four<0?"大戶持股比下降":"變化不大";
 return{code,latest:newest,rows:a,d1:one,d4:four,d8:eight,label};
}
function buildList(){
 const src=loaded?.stocks||{},arr=Object.entries(src).map(([k,w])=>summarize(k,w)).filter(Boolean);
 const q=query.trim().toUpperCase();
 let list=arr.filter(x=>!q||x.code.includes(q));
 if(kind==="GAIN")list=list.filter(x=>x.d4!=null&&x.d4>0).sort((a,b)=>b.d4-a.d4);
 if(kind==="FALL")list=list.filter(x=>x.d4!=null&&x.d4<0).sort((a,b)=>a.d4-b.d4);
 if(kind==="ALL")list=list.sort((a,b)=>(b.d4??-999)-(a.d4??-999)||a.code.localeCompare(b.code));
 return list;
}
function setup(){
 if(host||!document.getElementById("mainforcePanelV1"))return;
 host=document.createElement("section");host.id="tdccWeeklyPanelV1";host.className="panel";host.hidden=true;
 host.innerHTML=[
 '<details id="tdccDetails" open><summary><strong>🏦 集保大戶｜全市場免費自動更新</strong><small id="tdccBadge">每週官方資料</small></summary>',
 '<p class="tdcc-desc">使用 <a href="https://data.gov.tw/dataset/11452" target="_blank" rel="noopener noreferrer">TDCC 集保戶股權分散表</a>（政府開放資料）自動更新。<strong>這不是每天的券商分點「主力集中度」</strong>，兩種資料不混用，也不更動原本選股評分。</p>',
 '<div id="tdccStats" class="tdcc-stats"></div>',
 '<div class="tdcc-filters"><input type="search" id="tdccSearch" placeholder="搜尋股票代號，例 2330" aria-label="搜尋集保股票代號">',
 '<select id="tdccType" aria-label="大戶籌碼篩選"><option value="GAIN">四週持股增加</option><option value="FALL">四週持股下降</option><option value="ALL">全部股票</option></select></div>',
 '<div id="tdccRows" class="tdcc-rows"></div><div id="tdccDetail"></div>',
 '<p class="tdcc-desc">400張級以上 = 集保級距第12～15級（400,001股起）；1,000張級以上 = 第15級（1,000,001股起）。週增減以百分點 pp 表示。集保戶含各類專戶，不能據此直接辨認受益人或認定主力吸貨。</p>',
 '<p class="tdcc-desc">資料來源：<a href="https://opendata.tdcc.com.tw/getOD.ashx?id=1-5" target="_blank" rel="noopener noreferrer">集保官方CSV</a>，使用政府資料開放授權條款第1版；歷史補檔如有使用，註明公開封存來源。</p>',
 '</details>'
 ].join("");
 document.getElementById("mainforcePanelV1").insertAdjacentElement("beforebegin",host);
 host.addEventListener("input",e=>{if(e.target.id==="tdccSearch"){query=e.target.value;render()}});
 host.addEventListener("change",e=>{if(e.target.id==="tdccType"){kind=e.target.value;render()}});
 host.addEventListener("click",e=>{
  const card=e.target.closest("[data-tdcc-code]");
  if(card){openCode=openCode===card.dataset.tdccCode?"":card.dataset.tdccCode;render()}
 });
 sync();
}
async function load(force=false){
 if(loading||(!force&&loaded&&Date.now()-lastFetch<6*60*60*1000))return;
 loading=true;error="";try{
  const r=await fetch("./data/tdcc_weekly_concentration.json?source_v=1&ts="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw Error("官方週資料尚未發布（HTTP "+r.status+"）");
  const j=await r.json();
  if(j.schema!=="tdcc-weekly-ownership-v1"||!j.latest_week||!j.stocks||Object.keys(j.stocks).length<800)throw Error("官方週資料驗證失敗");
  if(j.latest_week>todayTW())throw Error("來源週次晚於今天，已停止使用");
  loaded=j;lastFetch=Date.now();
 }catch(e){error=e.message}finally{loading=false;render()}
}
function render(){
 if(!host||host.hidden)return;
 const banner=host.querySelector("#tdccStats");
 if(!loaded){
  banner.innerHTML='<p class="tdcc-empty">'+esc(error||"正在取得官方集保資料…")+'</p>';
  host.querySelector("#tdccRows").innerHTML="";
  host.querySelector("#tdccDetail").innerHTML="";
  return;
 }
 const count=Object.keys(loaded.stocks).length,list=buildList(),latest=loaded.latest_week;
 host.querySelector("#tdccBadge").textContent="官方週次 "+latest;
 banner.innerHTML='<div><small>官方資料週次</small><b>'+esc(latest)+'</b></div>'+
   '<div><small>涵蓋股票代號</small><b>'+count.toLocaleString()+" 檔</b></div>"+
   '<div><small>歷史週次</small><b>'+esc(String(loaded.weeks?.length||1))+" 週</b></div>"+
   '<div><small>符合目前篩選</small><b>'+list.length.toLocaleString()+" 檔</b></div>";
 let html="";
 for(const x of list.slice(0,40)){
  html+='<button type="button" class="tdcc-item" data-tdcc-code="'+esc(x.code)+'">'+
   '<span><b>'+esc(x.code)+'</b><small>'+esc(x.label)+'</small></span>'+
   '<span><strong>'+fmt(x.latest.big400)+'%</strong><small>400張級以上</small></span>'+
   '<span class="'+(x.d4!=null&&x.d4>0?"tdcc-up":x.d4!=null&&x.d4<0?"tdcc-down":"")+'">'+
   '<strong>'+esc(diff(x.d4))+'</strong><small>4週變動</small></span></button>';
 }
 if(!html)html='<p class="tdcc-empty">目前沒有符合條件的資料。首次建立歷史資料時，可能尚不足四週；可改選「全部股票」。</p>';
 if(list.length>40)html+='<p class="tdcc-desc">為避免手機負擔，僅顯示前40檔；可搜尋股票代號。</p>';
 host.querySelector("#tdccRows").innerHTML=html;
 const x=openCode?summarize(openCode,loaded.stocks[openCode]):null;
 host.querySelector("#tdccDetail").innerHTML=x?detail(x):"";
}
function detail(x){
 let rows=x.rows.slice(0,10),table=rows.map(w=>'<tr><td>'+esc(w.date)+'</td><td>'+fmt(w.big400)+'%</td><td>'+fmt(w.big1000)+'%</td><td>'+Number(w.large_holders||0).toLocaleString()+'</td></tr>').join("");
 const changed=x.d4==null?"四週歷史不足":x.d4>0?"大戶持股比增加，仍需量價與籌碼驗證":x.d4<0?"大戶持股比下降，留意籌碼分散":"四週持股比變動不大";
 return '<div class="tdcc-detail"><h3>'+esc(x.code)+'｜集保大戶週變化</h3>'+
   '<div class="tdcc-metrics"><div><small>400張級以上</small><strong>'+fmt(x.latest.big400)+'%</strong></div>'+
   '<div><small>1000張級以上</small><strong>'+fmt(x.latest.big1000)+'%</strong></div>'+
   '<div><small>1週變動</small><strong>'+esc(diff(x.d1))+'</strong></div>'+
   '<div><small>4週變動</small><strong>'+esc(diff(x.d4))+'</strong></div>'+
   '<div><small>8週變動</small><strong>'+esc(diff(x.d8))+'</strong></div></div>'+
   '<p class="tdcc-desc">'+esc(changed)+'；這是每週集保持股級距，不能推論單日券商分點買賣超。</p>'+
   '<table class="tdcc-table"><thead><tr><th>週次</th><th>400張級+</th><th>1000張級+</th><th>大額級距人數</th></tr></thead><tbody>'+table+'</tbody></table></div>';
}
function sync(){
 if(!host)return;host.hidden=!visible();
 if(!host.hidden){render();void load()}
}
function boot(){
 setup();
 document.addEventListener("radar:view-rendered",sync);
 document.addEventListener("radar:data-reloaded",()=>{lastFetch=0;void load(true)});
 document.addEventListener("click",e=>{if(e.target.closest?.("#tabs .tab,[data-close-mode]"))setTimeout(sync,50)});
 window.InukoTdccWeekly={status:()=>({latest:loaded?.latest_week||null,coverage:loaded?.stock_count||0,error})};
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
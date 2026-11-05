/* Mainforce radar v1: manually supplied broker-branch concentration only. */
(function(){
'use strict';
if(window.__INUKO_MAINFORCE_V1__)return;window.__INUKO_MAINFORCE_V1__=true;
const E=window.InukoMainforceCore;
if(!E){console.warn("Mainforce core missing");return}
const KEY="inuko.manual-mainforce-history.v1";
let rows=load(),host=null,closeDate="",selected="",search="",filter="ALL",clock=0,loading=false;
function load(){try{const a=JSON.parse(localStorage.getItem(KEY)||"[]");return Array.isArray(a)?a:[]}catch{return[]}}
function save(r){try{localStorage.setItem(KEY,JSON.stringify(r));rows=r;return true}catch(e){alert("本機儲存失敗，原資料未覆蓋。請匯出備份並減少筆數。");return false}}
const esc=x=>String(x==null?"":x).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=x=>x==null?"—":Number(x).toLocaleString("zh-TW",{maximumFractionDigits:2});
const sign=x=>x==null?"—":(x>0?"+":"")+fmt(x);
const today=()=>E.twDate();
const visible=()=>document.querySelector('.tab.active[data-view="close"]')&&!document.querySelector("#radarPanel")?.classList.contains("h60-screen-active");
function dl(name,text){
 const url=URL.createObjectURL(new Blob([text],{type:"text/csv;charset=utf-8"}));
 const a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function exportCsv(data){
 const header=["日期","股票代號","股票名稱","主力買賣超(張)","買賣家數差(家)","5日集中(%)","20日集中(%)","資料來源"];
 const records=[header];
 for(const r of data)records.push([r.date,r.code,r.name||"",r.net??"",r.houses??"",r.c5??"",r.c20??"",r.source||""]);
 return "\uFEFF"+records.map(a=>a.map(v=>'"'+String(v??"").replace(/"/g,'""')+'"').join(",")).join("\r\n")+"\r\n";
}
function setup(){
 if(host||!document.getElementById("radarPanel"))return;
 host=document.createElement("section");host.id="mainforcePanelV1";host.className="panel";host.hidden=true;
 host.innerHTML=[
 '<details id="mfDetails" open><summary><strong>📊 主力集中度｜分點籌碼轉折雷達</strong><small id="mfBadge">獨立觀察</small></summary>',
 '<p class="mf-tip">這裡是<strong>券商分點主力集中度</strong>，不是集保大戶持股或外資／投信。資料由你匯入，不會自動從付費平台取得，也不會影響原本波段分數。</p>',
 '<div id="mfStats" class="mf-stats"></div>',
 '<div class="mf-toolbar"><input id="mfSearch" type="search" placeholder="搜尋股票代號／名稱" aria-label="搜尋股票"><select id="mfFilter" aria-label="主力訊號篩選">',
 '<option value="ALL">全部個股</option><option value="TURN">回補／轉折觀察</option><option value="EASING">賣壓趨緩</option><option value="BEAR">20日仍偏空</option><option value="CURRENT">與收盤同日</option>',
 '</select></div><div id="mfList" class="mf-list"></div><div id="mfDetail"></div>',
 '<details id="mfImport"><summary>＋ 匯入／手動新增主力資料</summary>',
 '<p class="mf-tip">支援 CSV／TSV，至少包含「日期、股票代號」與一項主力欄位。5 日與 20 日集中度只使用來源原值；缺值不會補 0 或用法人資料代替。</p>',
 '<div class="mf-actions"><button type="button" id="mfTemplate">下載空白 CSV 範本</button><label class="mf-upload">選擇 CSV<input type="file" id="mfFile" accept=".csv,.tsv,text/csv,text/tab-separated-values"></label></div>',
 '<label class="mf-label">或貼上 CSV／TSV 文字<textarea id="mfPaste" rows="3" placeholder="日期,股票代號,股票名稱,主力買賣超(張),買賣家數差(家),5日集中(%),20日集中(%)"></textarea></label>',
 '<div class="mf-actions"><button type="button" id="mfPasteApply" class="mf-primary">解析並匯入</button></div>',
 '<form id="mfManualForm"><h3>手動新增單日資料</h3><div class="mf-grid">',
 '<label>資料日期<input type="date" name="date" required></label><label>股票代號<input name="code" maxlength="12" required placeholder="例如 2317"></label>',
 '<label>股票名稱<input name="name" maxlength="40" placeholder="選填"></label>',
 '<label>主力買賣超（張）<input name="net" type="number" step="1" placeholder="-4109"></label>',
 '<label>買賣家數差（家）<input name="houses" type="number" step="1" placeholder="15"></label>',
 '<label>5 日集中度（%）<input name="c5" type="number" step="0.01" placeholder="-16.8"></label>',
 '<label>20 日集中度（%）<input name="c20" type="number" step="0.01" placeholder="-22.1"></label>',
 '<label>資料平台<input name="source" maxlength="60" value="手動輸入／待核對"></label>',
 '</div><div class="mf-actions"><button class="mf-primary" type="submit">儲存單日資料</button></div></form>',
 '<div class="mf-actions mf-critical"><button type="button" id="mfExport">匯出本機 CSV 備份</button><button type="button" id="mfClear">清除本機紀錄</button></div>',
 '<p class="mf-tip">重複股票＋日期自動合併，不重複加總。此資料只存於本機瀏覽器，不同步其他手機。請定期匯出備份；勿上傳未授權的完整資料集至公開 GitHub。</p>',
 '</details><p id="mfFeedback" role="status" aria-live="polite"></p></details>'
 ].join("");
 document.getElementById("radarPanel").insertAdjacentElement("beforebegin",host);
 host.querySelector('[name="date"]').value=today();
 host.addEventListener("click",click);
 host.addEventListener("change",change);
 host.addEventListener("input",input);
 host.querySelector("#mfManualForm").addEventListener("submit",add);
 sync();
}
function feedback(msg,error=false){
 const el=host?.querySelector("#mfFeedback");
 if(el){el.textContent=msg;el.classList.toggle("mf-error",error)}
}
async function checkDate(force=false){
 if(loading||(!force&&Date.now()-clock<90000))return;
 loading=true;
 try{
  const r=await fetch("./data/current_manifest.json?mainforce="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw Error("manifest unavailable");
  const d=await r.json(),src=String(d.datasets?.decision_close_summary?.as_of||d.trade_date||"").slice(0,10);
  closeDate=/^\d{4}-\d{2}-\d{2}$/.test(src)?src:"";
 }catch(e){closeDate="";feedback("盤後來源日暫時無法確認，不會顯示同日有效標籤。",true)}
 finally{clock=Date.now();loading=false;render()}
}
function stats(){
 const all=E.allSummaries(rows,closeDate);
 return {all,turn:all.filter(x=>["RECOVERY_WATCH","REBOUND_WATCH"].includes(x.status)).length,
  same:all.filter(x=>x.freshness==="SAME_DAY").length};
}
function listing(){
 const {all}=stats(),q=search.trim().toUpperCase();
 let results=all.filter(x=>!q||x.code.includes(q)||(x.name||"").toUpperCase().includes(q));
 if(filter==="TURN")results=results.filter(x=>["RECOVERY_WATCH","REBOUND_WATCH"].includes(x.status));
 if(filter==="EASING")results=results.filter(x=>x.status==="SELL_EASING");
 if(filter==="BEAR")results=results.filter(x=>x.c20!=null&&x.c20<0);
 if(filter==="CURRENT")results=results.filter(x=>x.freshness==="SAME_DAY");
 const rank={RECOVERY_WATCH:0,REBOUND_WATCH:1,SELL_EASING:2,CONCENTRATING:3,MIXED:4,DISTRIBUTING:5,PARTIAL:6};
 return results.sort((a,b)=>(rank[a.status]??8)-(rank[b.status]??8)||b.date.localeCompare(a.date)||a.code.localeCompare(b.code));
}
function statusClass(x){
 return ["CONCENTRATING","REBOUND_WATCH","RECOVERY_WATCH"].includes(x)?"mf-positive":
  x==="DISTRIBUTING"?"mf-negative":"mf-muted";
}
function freshness(x){return x.freshness==="SAME_DAY"?"同收盤日":x.freshness==="STALE"?"歷史來源":x.freshness==="AHEAD"?"來源日超前":"日期待核對"}
function metric(label,value,cls=""){
 return '<div class="mf-metric"><small>'+esc(label)+'</small><strong class="'+cls+'">'+esc(value)+'</strong></div>';
}
function curve(history){
 const a=history.slice(0,10).reverse(),vals=a.flatMap(r=>[r.c5,r.c20]).filter(v=>v!=null);
 if(a.length<2||vals.length<2)return '<p class="mf-tip">需要兩期以上的有效集中度資料才會顯示趨勢圖。</p>';
 const low=Math.min(...vals,-1),high=Math.max(...vals,1),span=Math.max(high-low,.1);
 function path(k){
  return a.filter(x=>x[k]!=null).map((x,j,all)=>{
   const i=a.indexOf(x),px=25+280*i/Math.max(1,a.length-1),py=121-105*(x[k]-low)/span;
   return(j?"L":"M")+px.toFixed(1)+","+py.toFixed(1)
  }).join(" ");
 }
 return '<svg class="mf-chart" viewBox="0 0 340 145" role="img" aria-label="5日和20日集中度走勢"><line x1="24" x2="313" y1="123" y2="123" stroke="currentColor" opacity=".2"/>'+
  '<path d="'+path("c5")+'" fill="none" stroke="#229d78" stroke-width="2.6"/><path d="'+path("c20")+'" fill="none" stroke="#d2934d" stroke-width="2.6"/>'+
  '<text x="2" y="13" font-size="10" fill="currentColor">'+high.toFixed(1)+'%</text><text x="2" y="125" font-size="10" fill="currentColor">'+low.toFixed(1)+'%</text>'+
  '<text x="25" y="141" font-size="10" fill="currentColor">'+esc(a[0].date.slice(5))+'</text><text x="267" y="141" font-size="10" fill="currentColor">'+esc(a[a.length-1].date.slice(5))+'</text></svg>'+
  '<div class="mf-legend">● 5日集中度　<span>● 20日集中度</span></div>';
}
function detail(x){
 let table='<table class="mf-table"><thead><tr><th>日期</th><th>主力張數</th><th>家數差</th><th>5日</th><th>20日</th></tr></thead><tbody>';
 for(const r of x.history.slice(0,12))table+='<tr><td>'+esc(r.date.slice(5))+'</td><td>'+esc(sign(r.net))+'</td><td>'+esc(sign(r.houses))+'</td><td>'+esc(r.c5==null?"—":sign(r.c5)+"%")+'</td><td>'+esc(r.c20==null?"—":sign(r.c20)+"%")+'</td></tr>';
 table+='</tbody></table>';
 return '<div class="mf-detail"><div class="mf-line"><h3>'+esc(x.name||x.code)+'｜主力籌碼 <small>'+esc(x.code)+'</small></h3><button type="button" id="mfCloseDetail">收起</button></div>'+
  '<p class="mf-tip">資料日 '+esc(x.date)+' · '+esc(freshness(x))+' · 來源：'+esc(x.source||"手動提供")+'（未獨立核驗）</p>'+
  (x.freshness!=="SAME_DAY"?'<p class="mf-warning">資料日未與盤後收盤日一致，僅供歷史研究，不作當日買賣依據。</p>':"")+
  '<div class="mf-metrics">'+metric("5日集中度",x.c5==null?"—":sign(x.c5)+"%")+
  metric("20日集中度",x.c20==null?"—":sign(x.c20)+"%")+
  metric("5日變化",x.d5==null?"—":sign(x.d5)+" pp")+
  metric("20日變化",x.d20==null?"—":sign(x.d20)+" pp")+
  metric("當日買賣超",x.net==null?"—":sign(x.net)+" 張")+
  metric("買賣家數差",x.houses==null?"—":sign(x.houses)+" 家")+'</div>'+
  '<div class="mf-signal '+statusClass(x.status)+'">'+esc(x.label)+'<br><small>'+esc(x.reason)+'</small></div>'+
  curve(x.history)+table+
  '<p class="mf-tip">主力指券商分點統計，不等於辨認實際大戶。5日／20日數值依供應商原口徑，百分點變化以 pp 顯示。此模組不修改原選股分數與進場建議。</p></div>';
}
function annotateCards(){
 if(!visible())return;
 const map=new Map(E.allSummaries(rows,closeDate).map(x=>[x.code,x]));
 for(const card of document.querySelectorAll("#cards .card[data-code]")){
   card.querySelectorAll(".mf-card-evidence").forEach(x=>x.remove());
   const x=map.get(String(card.dataset.code||"").toUpperCase());
   if(!x)continue;
   const el=document.createElement("div");
   el.className="mf-card-evidence";
   const current=x.freshness==="SAME_DAY";
   el.innerHTML='<small>主力集中度｜'+esc(x.date)+' '+(current?'同收盤日':'歷史資料')+' · 本機匯入</small>'+
      '<span>5日 '+esc(x.c5==null?'—':sign(x.c5)+'%')+' · 20日 '+esc(x.c20==null?'—':sign(x.c20)+'%')+
      '｜'+esc(x.label)+'</span>';
   card.appendChild(el);
 }
}
function render(){
 if(!host||host.hidden)return;
 const s=stats(),a=listing();
 host.querySelector("#mfBadge").textContent="本機 "+s.all.length+" 檔";
 host.querySelector("#mfStats").innerHTML=
  metric("盤後收盤日",closeDate||"待確認")+metric("已匯入個股",s.all.length+" 檔")+
  metric("轉折觀察",s.turn+" 檔")+metric("同收盤日來源",s.same+" 檔");
 let html="";
 for(const x of a.slice(0,50)){
  html+='<button type="button" class="mf-item '+(selected===x.code?"selected":"")+'" data-mf-code="'+esc(x.code)+'">'+
    '<span class="mf-line"><b>'+esc(x.name||x.code)+' <small>'+esc(x.code)+'</small></b><small>'+esc(x.date)+' · '+esc(freshness(x))+'</small></span>'+
    '<span class="mf-line"><span class="'+statusClass(x.status)+'">'+esc(x.label)+'</span>'+
    '<small>5日 '+esc(x.c5==null?"—":sign(x.c5)+"%")+' / 20日 '+esc(x.c20==null?"—":sign(x.c20)+"%")+'</small></span></button>';
 }
 if(!html)html='<p class="mf-empty">'+(rows.length?"目前篩選下沒有符合的主力資料。":"目前沒有主力分點資料。展開下方匯入區，即可新增手動資料或 CSV。")+'</p>';
 if(a.length>50)html+='<p class="mf-tip">為保障手機流暢度，最多顯示 50 檔。可輸入代號搜尋。</p>';
 host.querySelector("#mfList").innerHTML=html;
 const x=s.all.find(v=>v.code===selected);
 host.querySelector("#mfDetail").innerHTML=x?detail(x):"";
 annotateCards();
}
function sync(){if(!host)return;host.hidden=!visible();if(!host.hidden){render();void checkDate()}}
function commit(newRows){
 const next=E.merge(rows,newRows);
 if(save(next)){feedback("成功合併 "+newRows.length+" 筆；同一代號和日期不重複新增。");render()}
}
async function fileImport(file){
 if(!file)return;
 if(file.size>E.MAX_BYTES){feedback("檔案大於 1.8 MB，請分批匯入。",true);return}
 try{commit(E.importCsv(await file.text(),today()))}catch(e){feedback("匯入失敗："+e.message,true)}
}
function add(e){
 e.preventDefault();
 const f=e.currentTarget,d={};
 for(const [k,v] of new FormData(f))d[k]=v;
 try{
  const rec=E.record(d);
  if(rec.date>today())throw Error("不能匯入未來日期");
  commit([rec]);selected=rec.code;
  for(const k of ["net","houses","c5","c20"])f.elements.namedItem(k).value="";
  render();
 }catch(error){feedback("新增失敗："+error.message,true)}
}
function click(e){
 const id=e.target.id;
 if(id==="mfTemplate"){dl("犬子主力集中度_空白範本.csv",E.csvTemplate);return}
 if(id==="mfPasteApply"){
  try{commit(E.importCsv(host.querySelector("#mfPaste").value,today()));host.querySelector("#mfPaste").value=""}
  catch(error){feedback("無法解析："+error.message,true)}
  return;
 }
 if(id==="mfExport"){dl("犬子主力集中度_本機備份.csv",exportCsv(rows));return}
 if(id==="mfClear"){
  if(rows.length&&confirm("確定清除本機的 "+rows.length+" 筆主力資料？請先匯出備份。")&&save([])){
   selected="";render();feedback("本機主力紀錄已清除");
  }return;
 }
 if(id==="mfCloseDetail"){selected="";render();return}
 const item=e.target.closest("[data-mf-code]");
 if(item){selected=selected===item.dataset.mfCode?"":item.dataset.mfCode;render()}
}
function change(e){
 if(e.target.id==="mfFile"){void fileImport(e.target.files?.[0]);e.target.value=""}
 if(e.target.id==="mfFilter"){filter=e.target.value;render()}
}
function input(e){if(e.target.id==="mfSearch"){search=e.target.value;render()}}
function boot(){
 setup();
 document.addEventListener("radar:view-rendered",sync);
 document.addEventListener("radar:cards-rendered",annotateCards);
 document.addEventListener("radar:data-reloaded",()=>{clock=0;void checkDate(true);sync()});
 document.addEventListener("click",e=>{if(e.target.closest?.("#tabs .tab,[data-close-mode]"))setTimeout(sync,50)});
 window.InukoMainforcePanel={status:()=>({recordCount:rows.length,closeDate,selected}),refresh:()=>{clock=0;void checkDate(true)}};
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
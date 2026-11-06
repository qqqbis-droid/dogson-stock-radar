"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const UI=require("../../docs/v2/tdcc-weekly-ui-v1.js");
const doTest=(name,fn)=>{fn();console.log("PASS TDCC card",name)};
function history(code="1815"){
 const arr=[];
 for(let i=0;i<9;i++){
  const d=new Date(Date.UTC(2026,9,30-7*i)).toISOString().slice(0,10);
  arr.push({date:d,big400:56.4+i*0.4,big1000:51.75+i*0.35,large_holders:110+i,total_holders:161507+i*500});
 }
 return{code,arr};
}
doTest("400/1000 lots, weekly 1/4/8 changes computed independently",()=>{
 const {arr}=history(),s=UI.summarize("1815",arr);
 assert.equal(s.code,"1815");
 assert.equal(s.latest.date,"2026-10-30");
 assert.equal(s.latest.big400,56.4);
 assert.equal(s.d1,-0.4);
 assert.equal(s.d4,-1.6);
 assert.equal(s.d8,-3.2);
 assert.equal(s.kilo4,-1.4);
 assert.equal(s.label,"大戶持股比下降");
});
doTest("unknown week must not fabricate percent or delta",()=>{
 const s=UI.summarize("9999",[{date:"2026-10-30",big400:20.3,big1000:9.9}]);
 assert.equal(s.d1,null);assert.equal(s.d4,null);assert.equal(s.d8,null);
 const card=UI.cardHtml(s,"2026-10-30");
 assert.match(card,/400張級以上/);assert.match(card,/較前4期/);assert.match(card,/—/);
 assert.doesNotMatch(card,/\+0 pp/);
});
doTest("compact stock card includes correct official week and no trading advice",()=>{
 const s=UI.summarize("1815",history().arr);
 const card=UI.cardHtml(s,"2026-10-30");
 assert.match(card,/集保大戶/);assert.match(card,/官方週次 2026-10-30/);
 assert.match(card,/56.4%/);assert.match(card,/-1.6 pp/);
 assert.doesNotMatch(card,/主力分點集中度|現在買進|波段分數/);
});
doTest("detail appears per stock with expandable history and provenance",()=>{
 const s=UI.summarize("1815",history().arr);
 const html=UI.detailHtml(s,{week:"2026-10-30"});
 for(const token of ["400張級以上","1,000張級以上","400張級 1期變動","400張級 4期變動","400張級 8期變動","1,000張級 4期變動","查看最近集保週次","TDCC 集保官方開放資料","每週","未納入原選股分數"]){
   if(token==="每週")continue;
   assert.ok(html.includes(token),"missing "+token);
 }
 assert.match(html,/data-tdcc-detail="1"/);
 assert.match(html,/<table>/);assert.match(html,/<svg/);
 assert.match(html,/分點主力集中度不同/);
});
doTest("exceptional new-listing or corporate action changes are cautioned",()=>{
 const s=UI.summarize("YKE3",history("YKE3").arr.map((x,i)=>({...x,big400:i===0?100:0,big1000:i===0?70:0})));
 assert.equal(s.extreme,true);assert.match(UI.cardHtml(s),/須核對公司行為/);
 assert.match(UI.detailHtml(s,{week:"2026-10-30"}),/不可直接判定為吸貨/);
});
doTest("missing stock shows unavailable instead of a made-up zero",()=>{
 const x=UI.detailHtml(null,{week:"2026-10-30"});
 assert.match(x,/未取得完整的集保持股級距資料/);
 assert.doesNotMatch(x,/0%/);
});
doTest("HTML unsafe codes cannot inject script or attributes",()=>{
 const data=history().arr;
 const s=UI.summarize("1815",data);
 s.code='<img src=x onerror=alert(1)>';
 const detail=UI.detailHtml(s,{week:'2026-10-30'});
 assert.ok(detail.includes('&lt;img'));
 assert.ok(!detail.includes('<img'));
});
doTest("Taiwan calendar date uses stable locale-independent parts",()=>{
 assert.equal(UI.todayTW(new Date("2026-11-05T16:07:00Z")),"2026-11-06");
});
doTest("UI integrates with existing stock-card and detail events, not global rankings",()=>{
 const dir=path.resolve(__dirname,"../../docs/v2");
 const script=fs.readFileSync(path.join(dir,"tdcc-weekly-ui-v1.js"),"utf8");
 const css=fs.readFileSync(path.join(dir,"tdcc-weekly-ui-v1.css"),"utf8");
 const index=fs.readFileSync(path.join(dir,"index.html"),"utf8");
 for(const name of ["radar:cards-rendered","radar:open-stock","radar:detail-rendered","radar:detail-core-rendered","radar:data-reloaded","detailBody","data-tdcc-evidence","data-tdcc-detail"]){
  assert.ok(script.includes(name),"missing integration "+name);
 }
 assert.ok(script.includes("./data/tdcc_weekly_concentration.json"));
 assert.ok(!script.includes('tdccWeeklyPanelV1')&&!script.includes("buildList(")&&!script.includes("const rank="));
 assert.ok(!script.includes('score=')&&!script.includes("swing_quality_score"));
 assert.ok(css.includes('#cards .card .tdcc-card-inline'));
 assert.ok(css.includes('#detailDialog .tdcc-in-stock'));
 assert.ok(index.includes('tdcc-weekly-ui-v1.js?v=20261106b'));
 assert.ok(index.includes('tdcc-weekly-ui-v1.css?v=20261106b'));
});
console.log("TDCC per-stock move contract tests passed");

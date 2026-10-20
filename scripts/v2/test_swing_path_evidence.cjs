#!/usr/bin/env node
'use strict';
// Never let the new route invent prices, treat a crossing as a trade,
// or change the existing score/rank/portfolio ownership.
const fs=require('node:fs'),assert=require('node:assert/strict');
const js=fs.readFileSync('docs/v2/swing-path-v1.js','utf8');
const css=fs.readFileSync('docs/v2/swing-path-v1.css','utf8');
const close=fs.readFileSync('docs/v2/close-ops-v1.js','utf8');
const detail=fs.readFileSync('docs/v2/detail-loading-guard-v2.js','utf8');
const html=fs.readFileSync('docs/v2/index.html','utf8');
const win={};
const lib=new Function('window',js+'\nreturn window.InukoSwingPath;')(win);
assert.equal(lib.version,'1.0');
const build='case-20261016',date='2026-10-16';
const z=(side,rank,lo,hi,over={})=>({
 build_id:build,trade_date:date,side,rank,low:lo,high:hi,
 freshness:'FRESH',structure_state:'ACTIVE',
 evidence:['20日高','成交密集區'],
 evidence_families:['price_structure','volume_structure'],
 source_status:{sources:['legacy-v1-migration-adapter']},
 ...over
});
const make=(zones,price=100.5,opts={})=>({
 code:'6209',view:'close',build_id:build,as_of:date+'T13:30:00+08:00',
 decision:{quote:{price},data_confidence:100,action_state:'WAIT_TRIGGER',lifecycle_stage:'SETUP',...opts},
 evidence:{hourly60:{trade_date:date,data_status:'OK',ma20_60:98,ma60_60:94,entry_light:'YELLOW'},foreign_date:date,trust_date:date},
 zones
});
const zones=[z('SUPPORT','S1',91,93),z('RESISTANCE','R1',104,105),z('RESISTANCE','R2',110,115)];
const evalPath=(shard,extra={})=>lib.evaluate(shard,{expectedBuild:build,expectedDate:date,allowed:true,...extra});
const path=evalPath(make(zones));
assert.equal(path.phase,'等待突破');
assert.equal(path.next,'R1 104～105');
assert.equal(path.steps[3].value,'110～115');
assert.equal(path.resistance.low,104);
assert(path.invalidation.includes('91'));
assert(lib.compactHtml(path).includes('目前階段')&&lib.compactHtml(path).includes('下一關卡'));
assert(lib.detailHtml(path).includes('關卡來源與驗證狀態'));
assert(!lib.detailHtml(path).includes('swing-path-steps'),'Stop repeating the four-step plan already shown in 3Q');
assert(lib.detailHtml(path).includes('模型結構整理'),'Historical evidence must be called model-derived');
const noR=evalPath(make(zones.filter(x=>x.side==='SUPPORT')));
assert.equal(noR.resistance,null);
assert(noR.next.includes('R1 待補'));
assert(noR.steps[3].value==='待補，不預測');
const orphanR2=evalPath(make(zones.filter(x=>x.rank!=='R1')));
assert.equal(orphanR2.extension,null,'R2 without verified R1 is not a valid sequence');
assert.equal(orphanR2.steps[3].value,'待補，不預測');
assert(!lib.detailHtml(noR).includes('104～105'));
const crossing=evalPath(make(zones,106));
assert.equal(crossing.phase,'突破後待回測');
assert.equal(crossing.promotionReady,false,'Crossing R1 alone is not a confirmed breakout');
assert.equal(crossing.checks.length,4);
assert(crossing.checks.some(x=>x.name==='相對大盤'&&!x.passed),'Unverified relative market cannot be made green');
assert(lib.detailHtml(crossing).includes('不能升級成已成立訊號'));
assert(!lib.detailHtml(crossing).includes('突破已確認'));
const guarded=make(zones,103,{action_state:'WAIT_PULLBACK'});
guarded.evidence.hourly60.entry_light='RED';
const sameVerdict=evalPath(guarded,{plan:{type:'LAYOUT',gate:'回踩 S1 守住並確認量價'}});
assert.equal(sameVerdict.phase,'回測承接待確認','Verified close-card stage must not contradict its expanded detail');
assert.equal(sameVerdict.action,'回踩 S1 守住並確認量價');
assert.equal(sameVerdict.checks.find(c=>c.name==='60分K結構').passed,false,'Red 60K must fail the upgrade check');
const unsafe=evalPath(make(zones,106,{action_state:'DO_NOT_CHASE'}));
assert(unsafe.phase.includes('風險優先'));
const expired=evalPath(make(zones.map(a=>({...a,trade_date:'2026-10-15'}))));
assert(!expired.support&&!expired.resistance);
const stale=evalPath(make(zones.map(a=>({...a,freshness:'STALE'}))));
assert(!stale.support&&!stale.resistance);
const older=evalPath({...make(zones),build_id:'old-build'});
assert.equal(older.known,false);
assert.equal(older.quote,100.5);assert(!older.support);
const prohibited=evalPath(make(zones),{allowed:false});
assert.equal(prohibited.known,false);
const missingPrice=evalPath(make(zones,null));
assert.equal(missingPrice.known,false);
const partial=evalPath(make(zones),{plan:{type:'PARTIAL',gate:'暫不建立新倉'}});
assert.equal(partial.kind,'verify');
assert(path.h60valid&&path.chipSame);
const ready3=evalPath(make(zones),{plan:{type:'LAYOUT',label:'等待布局',note:'同日驗證通過',gate:'回踩確認',ready:true,sessionOK:true}});
assert.equal(ready3.threeQ.lane,'READY');
assert.equal(ready3.threeQ.label,'布局優先・待觸發');
assert.equal(ready3.threeQ.gate,ready3.action,'Three questions must copy the SAME final action, not re-score');
const watch3=evalPath(make(zones),{plan:{type:'BREAKOUT',note:'先等回測',gate:'突破回測確認',ready:true,sessionOK:true}});
assert.equal(watch3.threeQ.lane,'WAIT');
assert.equal(watch3.threeQ.watch,watch3.next);
const risk3=evalPath(make(zones),{plan:{type:'NO_CHASE',note:'報酬／風險比不足',gate:'先不追',sessionOK:true}});
assert.equal(risk3.threeQ.lane,'BLOCKED','Risk classification must override normal S/R validity');
const partial3=evalPath(make(zones.filter(x=>x.side==='SUPPORT')),{plan:{type:'PARTIAL',note:'R1 待驗',sessionOK:true}});
assert.equal(partial3.threeQ.lane,'PENDING');
assert.equal(evalPath(make(zones),{allowed:false,plan:{type:'LAYOUT',ready:true,sessionOK:true}}).threeQ.lane,'PENDING','Stale quote must never appear layout ready');
assert.equal(evalPath(make(zones),{plan:{type:'LAYOUT',ready:false,sessionOK:true}}).threeQ.lane,'WAIT','Unconfirmed setup cannot claim ready');
const threeHtml=lib.threeQuestionHtml(ready3);
assert(threeHtml.includes('現在值得出手嗎？')&&threeHtml.includes('明天要盯哪個訊號？')&&threeHtml.includes('看錯時怎麼辦？'));
assert(threeHtml.includes('明日決策'),'Research board decision starts with one compact verdict');
assert(threeHtml.includes('非自動買賣指令')||threeHtml.includes('不是自動買賣指令'));
assert(!lib.threeQuestionHtml(risk3).includes('布局優先・待觸發'));
assert(!lib.threeQuestionHtml(null));
const bridge=fs.readFileSync('docs/v2/detail-loading-guard-v2.js','utf8');
assert(bridge.includes("view==='close'&&!ignite&&path"),'3Q only on close swing; daytrade and ignition remain untouched');
assert(bridge.includes("view==='close'&&!ignite?'':"),'Do not print redundant old action hero');
assert(bridge.includes('${swingThreeQ}')&&bridge.includes('data-inuko-decision-layout'),'Decision summary must lead the compact layout');
assert(bridge.includes("if(view==='close'&&!ignite&&path)"),'Only close swing gets new layout');
assert(bridge.includes("return;\n    }\n    box.body.innerHTML="),'Legacy live, ignition and daytrade must keep full detail');
assert(bridge.includes('data-inuko-research')&&bridge.includes('data-inuko-technical')&&bridge.includes('data-inuko-provenance'),'Expanded evidence must remain available');
assert(!js.slice(js.indexOf('function detailHtml(')).includes('<div class="swing-path-steps">'),'4-card repeat must be removed');
assert(html.includes('detail-loading-guard-v2.js?v=20261016route1&layout=20261020b&design=20261020b'),'Mobile detail script must bypass old cache');
assert(path.lens&&path.lens.pct>0&&path.lens.pct<100);
assert(lib.detailHtml(path).includes('價格結構位置'));
assert(lib.detailHtml(path).includes('S1｜防守')&&lib.detailHtml(path).includes('R1｜壓力'));
assert(lib.detailHtml(path).includes('<details class="swing-path-checks">'),'Do not show all evidence checks expanded');
assert.equal((lib.detailHtml(path).match(/<details/g)||[]).length,2,'Only two opt-in drilldowns inside structure section');
assert(lib.detailHtml(path).includes('獨立證據 2 類'));
assert(!noR.lens,'Never invent price location when R1 is absent');
assert(lib.detailHtml(noR).includes('價格位置待核對'));
assert(!lib.detailHtml(older).includes('價格結構位置'));
assert(path.facts.length>=0);
assert(css.includes('@media(max-width:510px)'),'Mobile route must be two-column');
assert(css.includes('.inuko-dossier>summary'),'Research disclosures must be thumb-friendly');
assert(html.includes('inuko-editorial-v3.css?v=20261020d'),'The final editorial layer must be active in production');
assert(html.indexOf('inuko-editorial-v3.css?v=20261020d')>html.indexOf('modern-v2.css'),'Editorial CSS should be loaded after old generic styles');
assert(require('node:fs').readFileSync('docs/v2/inuko-editorial-v3.css','utf8').includes('#cards .inuko-editorial-card .quote-strip'),'The large boxed quote in iPhone screenshots must be removed');
for(const tag of ['<script src="./swing-path-v1.js?v=20261020layout2&design=20261020b">','swing-path-v1.css?v=20261020layout2','close-ops-v1.js?v=20261016route1','detail-loading-guard-v2.js?v=20261016route1'])
 assert(html.includes(tag),'Missing deployed cache-busted asset: '+tag);
assert(close.includes('window.InukoSwingPath.evaluate(shard'),'Close card must use shared route');
assert(detail.includes('window.InukoSwingPath?.detailHtml?.(path)'),'Direct single-stock detail must use same route');
assert(!js.includes('target_price'),'No hidden predicted target-price feed');
console.log('PASS: swing path current build/date, price provenance, iPhone layout, no imaginary R2, breakout only pending retest');

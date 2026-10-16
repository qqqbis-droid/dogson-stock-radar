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
assert(lib.detailHtml(path).includes('模型結構整理'),'Historical evidence must be called model-derived');
const noR=evalPath(make(zones.filter(x=>x.side==='SUPPORT')));
assert.equal(noR.resistance,null);
assert(noR.next.includes('R1 待補'));
assert(noR.steps[3].value==='待補，不預測');
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
assert(css.includes('@media(max-width:510px)'),'Mobile route must be two-column');
for(const tag of ['<script src="./swing-path-v1.js?v=20261016route1">','swing-path-v1.css?v=20261016route1','close-ops-v1.js?v=20261016route1','detail-loading-guard-v2.js?v=20261016route1'])
 assert(html.includes(tag),'Missing deployed cache-busted asset: '+tag);
assert(close.includes('window.InukoSwingPath.evaluate(shard'),'Close card must use shared route');
assert(detail.includes('window.InukoSwingPath?.detailHtml?.(path)'),'Direct single-stock detail must use same route');
assert(!js.includes('target_price'),'No hidden predicted target-price feed');
console.log('PASS: swing path current build/date, price provenance, iPhone layout, no imaginary R2, breakout only pending retest');

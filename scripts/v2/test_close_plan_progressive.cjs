#!/usr/bin/env node
'use strict';
// Regression: on mobile, a long "Tomorrow" list must not block all cards
// while the very last stock-shard request finishes.
const fs=require('node:fs');
const assert=require('node:assert/strict');
const read=p=>fs.readFileSync(p,'utf8');
const js=read('docs/v2/close-ops-v1.js');
const swing=read('docs/v2/swing-path-v1.js');
const app=read('docs/v2/app.js');
const css=read('docs/v2/close-ops-v1.css');
const html=read('docs/v2/index.html');
assert(js.includes('IntersectionObserver(entries=>'),'Use viewport-based progressive loading');
assert(js.includes('observer.observe(card)'),'Each stock card must be observed independently');
assert(js.includes('const item=await shard(code,D.build)'),'Each stock must receive its own validated shard');
assert(js.includes('writeCard(card,classify(item?.decision||{code},item))'),'Update a card immediately after its own data returns');
assert(!js.includes('for(let i=0;i<candidates.length;i+=6)'),'Do not block all cards behind the full candidate list');
// The redesigned card exposes one concise action and the two validated
// price levels. Stop asserting the retired four redundant plan panels.
for(const title of ['明日留意','關鍵價位','S1 支撐','R1 壓力','已核對'])
  assert(js.includes(title),'Missing verified close-card summary: '+title);
assert(!js.slice(js.indexOf('function compact('),js.indexOf('function writeCard(')).includes('swing-path-compact'),
  'Retired four-grid must not duplicate the verified verdict');
assert(js.includes('validGlobal()&&same&&confidence!=null&&confidence>=80'),'Keep same-day and confidence gate');
assert(js.includes('zones.fresh'),'Never manufacture unsupported S1/R1');
assert(!app.includes('closeStrategy?"明日策略核對中"'),'Permanent placeholder not allowed');
assert(html.includes('close-ops-v1.js?v=20261016route1'),'iPhone must fetch new JS revision');
assert(html.includes('close-ops-v1.css?v=20261013color3'),'iPhone must fetch new CSS revision');
assert(html.includes('app.js?v=20261016ignitionrestore1'),'iPhone must fetch updated base cards');
assert(html.includes('chip-freshness-provenance.js?v=20261013gateupdate2'),'Close gate should recheck and rerender plans');
assert(css.includes('.cp-mini-levels')&&css.includes('.cp-mini-watch'),'One-line action and two-level layout styling present');
assert(app.includes('inuko-stock-card')&&app.includes('radarCardIdentity'), 'Both radar modes must reuse branded card identity');
assert(app.includes('radarCardScores')&&app.includes('radarActionLine'), 'Decision and score layout must be shared');
assert(read('docs/v2/app.css').includes('inuko-stock-card'), 'Brand styling must follow existing cream/forest tokens');
assert(read('docs/v2/detail-loading-guard-v2.js').includes('inuko-research-mast'), 'Internal research masthead must be installed');
assert(read('docs/v2/swing-path-v1.css').includes('.inuko-research-board'), 'Internal/external styles must agree');
assert(html.includes('design=20261020b'), 'iPhone must bypass stale UI assets');

const writeSource=js.slice(js.indexOf('function writeCard('),js.indexOf('function explainPending('));
assert(writeSource.startsWith('function writeCard('),'Card verdict updater must exist');
const writeCard=new Function('compact',writeSource+';return writeCard;')(()=>'<section data-close-plan></section>');
function fakeClasses(){
  const vals=new Set(['neutral']);
  return {add:(...xs)=>xs.forEach(x=>vals.add(x)),remove:(...xs)=>xs.forEach(x=>vals.delete(x)),contains:x=>vals.has(x)};
}
function checkColor(type,ready,expected){
  const label={textContent:''},dot={textContent:''},small={textContent:''};
  const line={classList:fakeClasses(),querySelector:s=>s==='b'?label:s==='span'?dot:s==='small'?small:null};
  const prior={outerHTML:''};
  const edge={};
  const style={setProperty:(property,value,priority)=>{edge[property]={value,priority}}};
  const card={isConnected:true,dataset:{},classList:fakeClasses(),style,querySelector:s=>s.includes('action-line')?line:s.includes('[data-close-plan]')?prior:null};
  writeCard(card,{type,ready,label:'模擬結論',date:'2026-10-13'});
  assert(card.classList.contains(expected),'Wrong left edge for '+type);
  assert(line.classList.contains(expected),'Border and text verdict must agree for '+type);
  assert.equal(card.dataset.closeTone,expected);
  const paint={go:'#1f5a46',wait:'#d39a2c','cp-blue':'#4b82ad',risk:'#b42318',stale:'#8c9590',neutral:'#dce2dc'}[expected];
  assert.deepEqual(edge['border-left'],{value:'6px solid '+paint,priority:'important'},'iOS needs a real inline 6px stripe for '+type);
  assert.deepEqual(edge['border-inline-start'],{value:'6px solid '+paint,priority:'important'},'RTL-safe edge must be painted too');
  assert(css.includes('#cards .card[data-close-tone="'+expected+'"]'),'Missing color CSS for '+type);
}
for(const [type,ready,tone] of [
 ['LAYOUT',true,'go'],['BREAKOUT',true,'cp-blue'],
 ['LAYOUT',false,'neutral'],['PARTIAL',false,'wait'],
 ['NO_CHASE',false,'risk'],['VERIFY',false,'stale'],['WATCH',false,'neutral']
])checkColor(type,ready,tone);

// The three lanes partition the original quality shortlist; they may never
// turn missing/invalid zone data or a no-chase verdict into "layout ready".
const laneSource=js.slice(js.indexOf('const laneFromPlan='),js.indexOf('const laneSnapshot='));
assert(laneSource,'Same-verdict lane mapping must exist');
const laneFromPlan=new Function(laneSource+';return laneFromPlan;')();
for(const [plan,lane] of [
  [{type:'LAYOUT',ready:true,sessionOK:true},'LAYOUT'],
  [{type:'LAYOUT',ready:false,sessionOK:true},'PENDING'],
  [{type:'BREAKOUT',ready:true,sessionOK:true},'WAIT'],
  [{type:'WATCH',ready:false,sessionOK:true},'WAIT'],
  [{type:'BREAKOUT',ready:false,sessionOK:false},'PENDING'],
  [{type:'NO_CHASE',ready:true,sessionOK:true},'BLOCKED'],
  [{type:'PARTIAL',ready:false,sessionOK:true},'PENDING'],
  [{type:'VERIFY',ready:false,sessionOK:false},'PENDING']
]) assert.equal(laneFromPlan(plan),lane,'Wrong no-chase gate for '+plan.type);
for(const lane of ['LAYOUT','WAIT','PENDING','BLOCKED']){
  assert(app.includes('kind:"plan",lane:"'+lane+'"'),'Missing actionable lane '+lane);
}
assert(js.includes('const evidence=await shard(code,build)'),'Never publish a lane without checking same-session evidence');
assert(js.includes('plan:classify(evidence?.decision||{code},evidence)'),'Counts and borders must share one final verdict');
assert(js.includes('radar:close-plan-lanes-updated'),'Only publish counts after complete audit');
// A genuine 20-day platform breakout can be examined without a fabricated R1.
// It must NEVER become a long entry just because the resistance source is empty.
const openSkySrc=js.slice(js.indexOf('function breakoutWithoutR1('),js.indexOf('function classify('));
assert(openSkySrc.startsWith('function breakoutWithoutR1('));
const openSky=new Function('n',openSkySrc+';return breakoutWithoutR1;')(v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v));
const evidence={platform_high20:100,break20:true,recent_breakout_age:0,vol_x:1.5,close_position_pct:82,dist20:3};
const engine={actionable:true,quote:{relative_volume:1.5},lifecycle_stage:'LAUNCH'};
const zones={supportFresh:true,resistanceFresh:false,support:{low:98}};
assert.deepEqual(openSky(evidence,engine,zones,102),{platform:100,riskPct:(102-98)/102*100,confirmed:false});
assert.equal(openSky(evidence,engine,{...zones,supportFresh:false},102),null,'No S1 may never bypass the safety gate');
assert.equal(openSky({...evidence,break20:false,recent_breakout_age:null},engine,zones,102),null,'Unknown breakout is not historical high');
assert.equal(openSky({...evidence,dist20:11},engine,zones,102),null,'Chasing extended positions must fail closed');
assert.equal(openSky({...evidence,vol_x:0.8},engine,zones,102),null,'Low-volume breakouts must fail closed');
assert.equal(openSky(evidence,engine,{...zones,support:{low:90}},102),null,'Wide downside risk must fail closed');
assert.equal(openSky({...evidence,retest_confirmed:true,breakout_confirmed:true}, {...engine,lifecycle_stage:'PULLBACK_CONFIRMED'},zones,102).confirmed,true,'Two independent breakout/retest proofs may move to layout');
assert(swing.includes('下一關｜前高回測'),'Use observed platform, never a made-up R1 target');
assert(swing.includes('不得把缺少 R1 解讀成無上漲阻力'),'Open-high mode must disclose source limitations');
console.log('PASS: progressive close cards, verified no-R1 breakout/retest route and preserved safety gates');

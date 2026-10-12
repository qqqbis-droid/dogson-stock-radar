#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync('docs/v2/close-ops-v1.js','utf8');
function block(a,b){const i=src.indexOf(a),j=src.indexOf(b,i);assert(i>=0&&j>i,'source block missing: '+a);return src.slice(i,j)}
const helpers=src.slice(src.indexOf('const n='),src.indexOf("const D="));
const functions=block('function findZones(','function writeCard(');
const build='close-test-20261012',date='2026-10-12';
const state={date,build,peers:new Map()};
const make= new Function('D','validGlobal','positions',
 helpers+'\n'+functions+'\nreturn {classify,compact};');
const {classify,compact}=make(state,()=>true,()=>[]);
const z=(side,rank,low,high)=>({side,rank,low,high,build_id:build,trade_date:date,structure_state:'ACTIVE',freshness:'FRESH'});
function shard(code,zones){
 return {view:'close',code,build_id:build,as_of:date+'T13:30:00+08:00',decision:{code,name:code,build_id:build,quote:{price:code==='1609'?39.3:247.5},data_confidence:100,action_state:'SMALL_TEST',lifecycle_stage:'LAUNCH',scores:{swing_quality_score:80,entry_position_score:75},primary_group:'電子'},zones,evidence:{}};
}
const ta=shard('1609',[z('SUPPORT','S1',38.39,38.73),z('RESISTANCE','R1',39.72,40.04)]);
const u=classify(ta.decision,ta),html=compact(u);
assert.equal(u.type,'NO_CHASE','Poor close-to-R1 reward/risk should veto entry');
assert.equal(u.ready,true);
assert(html.includes('38.35～38.75'),html.slice(0,400));
assert(html.includes('39.7～40.05'));
const tong=shard('6271',[z('SUPPORT','S1',241.27,243.31),z('SUPPORT','S2',231.35,238.25)]);
const p=classify(tong.decision,tong),ph=compact(p);
assert.equal(p.type,'PARTIAL');
assert.equal(p.label,'壓力待補');
assert.equal(p.ready,false);
assert(p.support&&!p.resistance);
assert(ph.includes('241～243.5'));
assert(ph.includes('待補（不推估）'));
assert(!ph.includes('整檔資料失效'));
const gate=make(state,()=>false,()=>[]);
const stale=gate.classify(ta.decision,ta),sth=gate.compact(stale);
assert.equal(stale.type,'VERIFY');
assert(sth.includes('38.35～38.75')&&sth.includes('39.7～40.05'));
assert(sth.includes('不可直接下單'));
const noS=shard('1609',[z('RESISTANCE','R1',39.72,40.04)]);
const q=classify(noS.decision,noS);
assert.equal(q.label,'支撐待補');
assert(compact(q).includes('沒有有效 S1'));
const legacy=fs.readFileSync('docs/v2/unified-score-freshness-v1.js','utf8');
const search=fs.readFileSync('docs/v2/universe-search.js','utf8');
const unifiedRender=legacy.slice(legacy.indexOf('  function decorateCards(){'),legacy.indexOf('  function normalizeScoreExplain(){'));
const searchHydrate=search.slice(search.indexOf('  async function hydrateVisibleCards(){'),search.indexOf('  function scheduleHydration('));
assert(unifiedRender.includes('data-ahd-strip')&&!unifiedRender.includes('cardStrip(d)'),'Legacy afterhours decorator must not create duplicate verdict cards');
assert(searchHydrate.includes('data-ahd-strip')&&!searchHydrate.includes('applyShard('),'Full-market search must never draw a second stock verdict');
console.log('PASS: S1/R1 individually visible; absent R1 preserves S1, no manufactured price/risk; stale session retains reference-only zones.');

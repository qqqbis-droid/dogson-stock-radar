#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const app=fs.readFileSync('docs/v2/app.js','utf8');
const html=fs.readFileSync('docs/v2/index.html','utf8');
assert(app.includes('data-live-evidence-gate'),'Must show an explicit source-unavailable panel');
assert(app.includes('const liveUnavailable=liveMission&&noExplicitSelection'),'Empty live radar is a truthful state');
assert(app.includes('d.action_state!=="DATA_STALE"'),'Exclude stale execution candidates by default');
assert(app.includes('&&d.freshness==="LIVE"'),'Require the live session');
assert(app.includes('&&num(d.quote?.price)!=null&&num(d.quote?.price)>0'),'Require observed priced evidence');
assert(app.includes('&&num(d.data_confidence)>=60'),'Require minimum confidence');
assert(app.includes('&&num(d.scores?.[cfg.scoreKey])!=null'),'Reject empty score recommendations');
assert(app.includes('const noExplicitSelection=!q&&!hasNonSearchFilter()&&!window.RadarFavorites?.only?.()'),'Individual search must retain unverified stocks for inspection');
assert(app.includes('資料待驗 · 不列排名'),'Do not rank stale 1101 as a selected opportunity');
assert(html.includes('app.js?v=20261015livegate1'),'iPhone must refresh revised app bundle');
console.log('PASS: live screens show only verified candidates by default, retain search and honest unavailable state');

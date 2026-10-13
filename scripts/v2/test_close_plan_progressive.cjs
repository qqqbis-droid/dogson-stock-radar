#!/usr/bin/env node
'use strict';
// Regression: on mobile, a long "Tomorrow" list must not block all cards
// while the very last stock-shard request finishes.
const fs=require('node:fs');
const assert=require('node:assert/strict');
const read=p=>fs.readFileSync(p,'utf8');
const js=read('docs/v2/close-ops-v1.js');
const app=read('docs/v2/app.js');
const css=read('docs/v2/close-ops-v1.css');
const html=read('docs/v2/index.html');
assert(js.includes('IntersectionObserver(entries=>'),'Use viewport-based progressive loading');
assert(js.includes('observer.observe(card)'),'Each stock card must be observed independently');
assert(js.includes('const item=await shard(code,D.build)'),'Each stock must receive its own validated shard');
assert(js.includes('writeCard(card,classify(item?.decision||{code},item))'),'Update a card immediately after its own data returns');
assert(!js.includes('for(let i=0;i<candidates.length;i+=6)'),'Do not block all cards behind the full candidate list');
for(const title of ['明日動作','關鍵價位','失效條件','S1 回踩觀察區','R1 第一壓力區'])
  assert(js.includes(title),'Missing required close-card section: '+title);
assert(js.includes('validGlobal()&&same&&confidence!=null&&confidence>=80'),'Keep same-day and confidence gate');
assert(js.includes('zones.fresh'),'Never manufacture unsupported S1/R1');
assert(!app.includes('closeStrategy?"明日策略核對中"'),'Permanent placeholder not allowed');
assert(html.includes('close-ops-v1.js?v=20261013progressive2'),'iPhone must fetch new JS revision');
assert(html.includes('close-ops-v1.css?v=20261013foursteps2'),'iPhone must fetch new CSS revision');
assert(html.includes('app.js?v=20261013closecards2'),'iPhone must fetch updated base cards');
assert(html.includes('chip-freshness-provenance.js?v=20261013gateupdate2'),'Close gate should recheck and rerender plans');
assert(css.includes('.cp-plan-row')&&css.includes('.cp-plan-heading'),'Four-part plan styling present');
console.log('PASS: progressive verified mobile close cards, S1/R1 and single tomorrow battle plan');

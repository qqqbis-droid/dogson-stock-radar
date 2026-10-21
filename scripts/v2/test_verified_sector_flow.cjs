#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync('docs/v2/market-capital-renderer.js','utf8');
const page=fs.readFileSync('docs/v2/index.html','utf8');
const a=source.indexOf('function closeRankInfo('),b=source.indexOf('function flowAuditText(',a);
assert(a>=0&&b>a,'No canonical sector rank validation');
const check=new Function('mn',source.slice(a,b)+'\nreturn closeRankInfo;')(
 v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v));
const day='2026-10-21',old='2026-10-20';
const stock={primary_group:'AI伺服器ODM',latest_date:day,today_amount_100m:17.6};
const reconciled={trade_date:day,groups:{AI伺服器ODM:{
 rank_eligible:true,rank_status:'RECONCILED',rank_trade_date:day,rank_amount_100m:17.61,rank_lots:862,
 reconciled:true,member_count:6,verified_count:6
}}};
let info=check(stock,reconciled,day);
assert(info.confirmed&&info.rankEligible&&info.rankAmount===17.61);
let rebuilt={trade_date:day,groups:{AI伺服器ODM:{
 rank_eligible:true,rank_status:'REBUILT_ALL_MEMBERS',rank_trade_date:day,
 rank_amount_100m:22.5,rank_lots:900,rank_full_member_coverage:true,
 reconciled:false,member_count:6,verified_count:6
}}};
info=check({...stock,latest_date:old},rebuilt,day);
assert(info.rankEligible&&info.rebuilt&&!info.confirmed,'Full valid same-day stocks may be rebuilt even if aggregate is old');
assert.equal(info.rankAmount,22.5,'New rank must use fully recalculated same-day shares, NOT yesterday amount');
assert.equal(check(stock,rebuilt,day).rankEligible,false,'Mismatched status/source date must not rank');
assert.equal(check({...stock,latest_date:old},rebuilt,'2026-10-22').rankEligible,false,'Never promote old data to next session');
assert.equal(check(stock,null,day).rankEligible,false,'Absent detail ledger cannot rank');
const incomplete={trade_date:day,groups:{AI伺服器ODM:{
 rank_eligible:false,rank_status:'INCOMPLETE',member_count:6,verified_count:5,
 sample_eligible:true,sample_trade_date:day,sample_scope:'SAME_DAY_MATCHED_STOCKS_ONLY',
 sample_amount_100m:1000,sample_lots:2200
}}};
info=check(stock,incomplete,day);
assert(!info.rankEligible&&info.sampleReady,'Partial stock subset may be shown ONLY outside ranked list');
const conflict={trade_date:day,groups:{AI伺服器ODM:{
 rank_eligible:true,rank_status:'RECALCULATED_SOURCE_DISAGREEMENT',
 rank_trade_date:day,rank_evidence_source:'COMPLETE_SAME_DAY_STOCK_ROWS',
 rank_full_member_coverage:true,reconciled:false,member_count:6,verified_count:6,
 rank_amount_100m:28.8,rank_lots:1110
}}};
info=check(stock,conflict,day);
assert(info.rankEligible&&info.recalculated&&!info.confirmed,'Six of six dated constituent flows may rank independently of disputed legacy aggregate');
assert.equal(info.rankAmount,28.8,'Use current individual-stock net, not conflicting source group total');
assert(!check(stock,conflict,'2026-10-22').rankEligible,'Never rank stale row tomorrow');
const partialConflict={...conflict,groups:{AI伺服器ODM:{...conflict.groups.AI伺服器ODM,verified_count:5}}};
assert(!check(stock,partialConflict,day).rankEligible,'Do not let incomplete current stocks become ranked via discrepancy fallback');
assert(source.includes('recalculated')&&source.includes('同日逐檔重算・舊彙總差異'),'Disagreeing aggregate must carry a distinct audit label on rank card');
assert(source.includes('資金流入排行')&&source.includes('資金流出排行'),'Both complete-sector rankings required');
assert(source.includes('eligible.filter(t=>t.info.rankAmount>0)'),'Rank only verified full groups');
assert(source.includes('未具排名資格')&&source.includes('不依金額排序'),'Incomplete sectors must remain outside the ranking');
assert(source.includes('eligible.filter(t=>t.info.rankAmount>0)') && source.includes('eligible.filter(t=>t.info.rankAmount<0)'), 'Only full same-date sectors may be ranked in either direction');
assert(!source.includes('sampleCards.join('), 'Partial per-stock sample cards must never enter ranked lists');
assert(source.includes('缺值不能當零') && source.includes('不拿部分樣本'), 'No hidden promotion of missing or partial evidence');
assert(source.includes('法人來源日')&&source.includes('歷史估算涵蓋（非逐檔有效）'),'Preserve actual legacy source disclosure');
assert(source.includes('犬子雷達追蹤池'),'Sector rank must disclose tracked-universe denominator');
assert(source.includes('intervalSection(')&&source.includes('非官方保證界限'),'Uncertainty must not be sold as certified ordering');
assert(source.includes('data-turnover-heat')&&source.includes('非法人買賣')&&source.includes('heatDate===day'),'Turnover heat must remain a separately labeled and date-matched noninstitutional indicator');
assert(page.includes('market-capital-renderer.js?v=20261022autosync3'),'Mobile cache must load complete-sector-first renderer');
assert(source.includes('data-capital-build')&&source.includes('data-capital-ranked'),'Live capital ranking must show the actual active build and ranked count');
assert(source.includes("window.setInterval(capitalRecheckOnReturn,45000)")&&source.includes("window.addEventListener('pageshow',capitalRecheckOnReturn)"),'iPhone web views must retry version checks on wake and periodically');
assert(source.includes("close?mset(m,'capital_close_members'):Promise.resolve(null)"),'Missing ledger must not silently become 0 ranks');
assert(source.includes("ledger?.build_id!==m.active_build_id")&&source.includes("Object.keys(groups).length!==(capital?.rows?.length||0)"),'Group version/count mismatch must fail rather than render stale cards');
assert(source.includes('if(seq!==MCR.renderSeq)return'),'Old async responses must not overwrite a new render');
console.log('PASS: version-visible, self-healing iPhone capital ranking plus strict same-build ledger validation');

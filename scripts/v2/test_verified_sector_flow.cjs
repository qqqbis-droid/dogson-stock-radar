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
const rows=[
 {code:'1111',valid:true,foreign_date:day,trust_date:day,estimated_amount_100m:10,net_lots:200,close_price:120},
 {code:'2222',valid:true,foreign_date:day,trust_date:day,estimated_amount_100m:7.61,net_lots:662,close_price:230}
];
const baseline={
 rank_eligible:true,rank_status:'RECONCILED',rank_trade_date:day,rank_amount_100m:17.61,
 rank_lots:862,reconciled:true,rank_evidence_source:'COMPLETE_SAME_DAY_STOCK_ROWS',
 rank_full_member_coverage:true,sample_trade_date:day,member_count:2,verified_count:2,stocks:rows
};
const stock={primary_group:'AI伺服器ODM',latest_date:day,today_amount_100m:17.61,today_lots:862};
const ledger=(row=baseline,date=day)=>({trade_date:date,groups:{AI伺服器ODM:row}});
let info=check(stock,ledger(),day);
assert(info.confirmed&&info.rankEligible&&info.rankAmount===17.61,'Independently matched same-session aggregate must rank');
info=check({...stock,latest_date:old,today_amount_100m:-88},ledger(),day);
assert(info.rankEligible&&info.rebuilt&&!info.confirmed,'OLD aggregate date must not remove complete current per-stock evidence');
assert.equal(info.rankAmount,17.61,'Do not replace current per-stock net with previous-day aggregate');
info=check({...stock,today_amount_100m:999},ledger(),day);
assert(info.rankEligible&&info.recalculated&&!info.confirmed,'Conflicting same-day group aggregate is only an audit note');
assert(!check(stock,ledger(baseline,old),day).rankEligible,'Previous-session ledger must not rank');
assert(!check(stock,ledger(), '2026-10-22').rankEligible,'Old ledger must not enter a future session');
assert(!check(stock,null,day).rankEligible,'Missing ledger must not rank');
assert(!check(stock,ledger({...baseline,verified_count:1}),day).rankEligible,'Partial coverage does not qualify');
assert(!check(stock,ledger({...baseline,stocks:rows.slice(0,1)}),day).rankEligible,'Missing constituent cannot qualify');
assert(!check(stock,ledger({...baseline,stocks:[{...rows[0],foreign_date:old},rows[1]]}),day).rankEligible,'Stale source constituent cannot qualify');
assert(!check(stock,ledger({...baseline,rank_amount_100m:19}),day).rankEligible,'Mismatched per-stock sum must not qualify');
assert(!check(stock,ledger({...baseline,rank_evidence_source:'INCOMPLETE_STOCK_ROWS'}),day).rankEligible,'Unverified evidence source cannot qualify');
assert(!check(stock,ledger({...baseline,rank_full_member_coverage:false}),day).rankEligible,'Incomplete-member flag cannot qualify');
assert(!check(stock,ledger({...baseline,rank_eligible:false}),day).rankEligible,'Backend veto must be respected');
const incomplete={...baseline,rank_eligible:false,rank_status:'INCOMPLETE',verified_count:1,
 sample_eligible:true,sample_trade_date:day,sample_scope:'SAME_DAY_MATCHED_STOCKS_ONLY',
 sample_amount_100m:1000,sample_lots:2200};
assert(!check(stock,ledger(incomplete),day).rankEligible,'Partial samples must remain unranked');
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
assert(page.includes('market-capital-renderer.js?v=20261022legacyfold2'),'Mobile cache must load complete-sector-first renderer');
assert(source.includes('data-capital-build')&&source.includes('data-capital-ranked'),'Live capital ranking must show the actual active build and ranked count');
assert(source.includes("window.setInterval(capitalRecheckOnReturn,45000)")&&source.includes("window.addEventListener('pageshow',capitalRecheckOnReturn)"),'iPhone web views must retry version checks on wake and periodically');
assert(source.includes("close?mset(m,'capital_close_members'):Promise.resolve(null)"),'Missing ledger must not silently become 0 ranks');
assert(source.includes("ledger?.build_id!==m.active_build_id")&&source.includes("Object.keys(groups).length!==(capital?.rows?.length||0)"),'Group version/count mismatch must fail rather than render stale cards');
assert(source.includes('if(seq!==MCR.renderSeq)return'),'Old async responses must not overwrite a new render');

// Production artifact integration: verify actual capital rows against same-build
// constituent ledger, not just flags or previous-day summary dates.
const path=require('node:path');
const root=path.resolve('docs/v2');
const manifestPath=path.join(root,'data/current_manifest.json');
if(fs.existsSync(manifestPath)){
 const m=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
 const cmeta=m.datasets?.capital_close_context,lmeta=m.datasets?.capital_close_members;
 if(cmeta&&lmeta){
  const load=meta=>{
   const rel=String(meta.url||'').replace(/^\.\//,'');
   assert(rel.startsWith('data/builds/'),'Unexpected capital dataset location');
   return JSON.parse(fs.readFileSync(path.join(root,rel),'utf8'));
  };
  const capital=load(cmeta),led=load(lmeta),tradingDay=String(cmeta.as_of||m.trade_date||'').slice(0,10);
  assert.equal(led.build_id,m.active_build_id,'Ledger is not the current atomic build');
  assert.equal(led.trade_date,tradingDay,'Ledger trade date differs from capital context');
  const evaluations=capital.rows.map(x=>({name:x.primary_group,source:x.latest_date,info:check(x,led,tradingDay)}));
  assert.equal(evaluations.length,Object.keys(led.groups).length,'Capital universe size mismatch');
  const complete=evaluations.filter(e=>{
   const g=led.groups[e.name];
   return g&&g.rank_eligible===true&&g.member_count>0
     &&g.verified_count===g.member_count&&g.rank_trade_date===tradingDay
     &&g.rank_evidence_source==='COMPLETE_SAME_DAY_STOCK_ROWS';
  });
  for(const e of complete)assert(e.info.rankEligible,'Complete stock evidence incorrectly omitted: '+e.name);
  const older=complete.filter(e=>String(e.source||'').slice(0,10)<tradingDay).length;
  console.log('LIVE capital eligible '+evaluations.filter(e=>e.info.rankEligible).length+'/'+evaluations.length
              +' complete '+complete.length+' outdated legacy summaries '+older+' build '+m.active_build_id);
 }
}


// UI-only regression: keep the whole sorted list intact, preserve ranks 4+,
// and fold each direction independently with a native keyboard-friendly details.
const rankStart=source.indexOf(' const rankBoard='),rankEnd=source.indexOf(' const intervalCard=',rankStart);
assert(rankStart>=0&&rankEnd>rankStart,'Missing ranked sector board');
const rankRenderer=new Function('rankCard',source.slice(rankStart,rankEnd)+'\nreturn rankBoard;')(
 (entry,i,dir)=>'<article data-test-rank="'+dir+'-'+(i+1)+'">'+entry.label+'</article>'
);
const seven=Array.from({length:7},(_,i)=>({label:'G'+(i+1)}));
for(const dir of ['in','out']){
 const html=rankRenderer(dir==='in'?'資金流入排行':'資金流出排行',seven,dir);
 const gate='data-capital-overflow="'+dir+'"';
 assert(html.includes(gate),'Missing independent '+dir+' fold');
 assert(html.includes('展開其餘 4 個族群（第 4～7 名）'),'Hidden rank count must be exact');
 const cutoff=html.indexOf('<details class="capital-rank-overflow"');
 assert(cutoff>0,'Expected native details for ranks 4+');
 assert.equal((html.slice(0,cutoff).match(/<article /g)||[]).length,3,'Only top three visible by default');
 assert.deepEqual([...html.matchAll(/data-test-rank="(in|out)-(\d+)"/g)].map(x=>Number(x[2])),
  [1,2,3,4,5,6,7],'Every rank must keep its original ordered index');
 assert(html.slice(cutoff).includes('data-test-rank="'+dir+'-4"'),'Rank four belongs inside fold');
 assert(!/<details class="capital-rank-overflow"[^>]*\bopen\b/.test(html),'Ranks 4+ must be initially collapsed');
}
for(const n of [0,1,2,3]){
 const html=rankRenderer('資金流入排行',seven.slice(0,n),'in');
 assert(!html.includes('data-capital-overflow'),'No pointless expander for '+n+' ranks');
 assert.equal((html.match(/<article /g)||[]).length,n,'Show all when no more than three');
}
assert(source.includes('capital-rank-overflow[open] .capital-rank-close-text'),
 'Expanded summary must offer a clear collapse label');
// Explanatory copy is preserved but moved BELOW ranked inflow and outflow,
 // behind a closed native fold, to keep the first screen actionable on iPhone.
const compactIndex=source.indexOf('box.innerHTML=shortInfo');
const inflowIndex=source.indexOf("rankBoard('資金流入排行',inflow,'in')",compactIndex);
const outflowIndex=source.indexOf("rankBoard('資金流出排行',outflow,'out')",compactIndex);
const foldIndex=source.indexOf(' +auditFold',compactIndex);
assert(compactIndex>=0&&inflowIndex>compactIndex&&outflowIndex>inflowIndex&&foldIndex>outflowIndex,
 'Compact date/count must appear first, full audit fold must follow both ranked boards');
assert(source.includes('data-capital-rank-mini'),'Small inline date and eligible-sector count required');
assert(source.includes('<details class="capital-estimates capital-method-fold" data-capital-method-fold>'),
 'Provenance requires an initially CLOSED native expandable detail');
assert(!/<details class="capital-estimates capital-method-fold"[^>]*\\bopen\\b/.test(source),
 'Audit notes should not start expanded');
assert(source.includes('資料來源與排名說明（含版本核對）'),
 'Explain where detailed provenance and version controls moved');
assert(source.includes('${buildStamp}${rankingScope}'),
 'Version recheck button and evidence methodology must remain accessible');
assert(source.includes('data-capital-recheck')&&source.includes('data-capital-rank-scope'),
 'No loss of provenance or version recheck function');
console.log('PASS: inflow/outflow Top 3 visible; all other original positions collapsible without changing scores');

console.log('PASS: version-visible, self-healing iPhone capital ranking plus strict same-build ledger validation');


// Capital-sector constituent links use the SAME authoritative, atomic close
// wave score as the existing per-stock swing-detail modal.
const detailSource=fs.readFileSync('docs/v2/capital-stock-breakdown.js','utf8');
const start=detailSource.indexOf('function officialSwing(');
const end=detailSource.indexOf('function paintScores(',start);
assert(start>=0&&end>start,'Official build-matched score accessor not found');
const swingScore=new Function('num',detailSource.slice(start,end)+'\nreturn officialSwing;')(
 v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v));
const build='build-test';
assert.equal(swingScore({build_id:build,scores:{swing_quality_score:63.7}},build),63.7);
assert.equal(swingScore({build_id:build,scores:{swing_quality_score:0}},build),0,'Zero is a real, not missing, score');
for(const x of [{build_id:'different',scores:{swing_quality_score:85}},
                {build_id:build,scores:{}},{build_id:build,scores:{swing_quality_score:null}},
                {build_id:build,scores:{swing_quality_score:101}}]){
 assert.equal(swingScore(x,build),null,'Stale, missing or invalid scores must be hidden');
}
const cardStart=detailSource.indexOf('function stock(s){');
const cardEnd=detailSource.indexOf('function detail(g){',cardStart);
assert(cardStart>=0&&cardEnd>cardStart,'Per-stock amount card missing');
const makeStock=new Function('num','amt','esc','fmt','lots',
 detailSource.slice(cardStart,cardEnd)+'\nreturn stock;')(
 v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v),
 v=>String(v),v=>String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;'),
 v=>String(v),v=>String(v));
const html=makeStock({code:'2317',name:'鴻海',estimated_amount_100m:76.43,valid:true,
 net_lots:30000,foreign_lots:29500,trust_lots:500,close_price:250});
assert(html.includes('data-cms-stock-card="2317"'),'Whole stock amount tile is the click target');
assert(html.includes('data-cms-wave-score="2317"'),'Wave quality badge belongs to matching stock code');
assert(html.includes('波段分數：待載入'),'Async data must never invent a score');
assert(html.includes('data-stock-code="2317"'),'Keyboard-accessible stock-name button must remain');
assert(detailSource.includes("scoreMeta=m.datasets?.decision_close_index"),'Read existing 24-item Wave 2.0 index, never recalculate score');
assert(detailSource.includes("String(source.as_of||'').slice(0,10)!==requestedDay"),'Score trade day must match stock flows');
assert(detailSource.includes("r.build_id!==requestedBuild"),'Do not mix index from another atomic build');
assert(detailSource.includes("detail:{code,view:'close',closeMode:'swing'}"),
 'Tile must open existing CLOSE swing detail, not a generic link');
assert(detailSource.includes("host.addEventListener('click',e=>")&&detailSource.includes('e.preventDefault();e.stopPropagation()'),
 'Capture stock taps before parent sector collapses');
assert(detailSource.includes("scoreEpoch++")&&detailSource.includes('scoresByCode=null'),
 'New data builds must invalidate old score badges');
assert(page.includes('capital-stock-breakdown.js?v=20261022sourceaudit2'),'Mobile cache must load new stock score cards');
// Integration with actual date-frozen model, if available in build workspace.
const manifest=JSON.parse(fs.readFileSync('docs/v2/data/current_manifest.json','utf8'));
const scoreMeta=manifest.datasets?.decision_close_index;
if(scoreMeta?.url){
 const locate=meta=>require('node:path').join('docs/v2',String(meta.url).replace(/^\.\//,''));
 const index=JSON.parse(fs.readFileSync(locate(scoreMeta),'utf8'));
 assert(Array.isArray(index)&&index.length>0,'Missing model index');
 const known=index.find(r=>r?.scores?.swing_quality_score!=null);
 assert(known,'No canonical swing quality scores to display');
 assert.equal(known.build_id,manifest.active_build_id,'Wave index build mismatch');
 const shardFile=require('node:path').join('docs/v2/data/builds',manifest.active_build_id,
                                  'stock-shards/close',String(known.code)+'.json');
 assert(fs.existsSync(shardFile),'Score-bearing stock must have full close research card');
 const shard=JSON.parse(fs.readFileSync(shardFile,'utf8'));
 assert.equal(shard.decision?.scores?.swing_quality_score,known.scores.swing_quality_score,
  'Wave badge and detail card MUST show the exact same original value');
 console.log('LIVE stock swing detail matched:',known.code,known.scores.swing_quality_score,manifest.active_build_id);
}
console.log('PASS: original wave score displayed on sector stocks and full swing card opens without score recomputation');


// Provenance UX: old 10/20 aggregate is audit-only, never a headline nor a
// reason to deny independently verified 10/21 stock rankings.
const auditSource=fs.readFileSync('docs/v2/capital-stock-breakdown.js','utf8');
const marketSource=fs.readFileSync('docs/v2/market-capital-renderer.js','utf8');
const auditRankStart=marketSource.indexOf(' const rankMore=(view,x,a)=>'),auditRankEnd=marketSource.indexOf(' const rankCard=',auditRankStart);
assert(auditRankStart>=0&&auditRankEnd>auditRankStart,'Cannot find ranked sector summary');
const auditRankMore=new Function('mmoney','mlots','mesc','memberButtons','day',
 marketSource.slice(auditRankStart,auditRankEnd)+'\nreturn rankMore;')(
 v=>String(v),v=>String(v),v=>String(v),()=>'<div class="members"></div>','2026-10-21');
const rankHtml=auditRankMore('close',{primary_group:'AI伺服器ODM'},{rankAmount:133.1,rankLots:61083.1,verified:6,members:6,sourceDay:'2026-10-20'});
assert(rankHtml.includes('當日資料日期</span><b>2026-10-21</b>'),'Current day stays prominent');
assert(rankHtml.includes('6/6 檔 · 100%'),'Coverage must remain shown');
assert(!rankHtml.includes('原族群彙總來源日</span>'),'Old date should not be an upfront metric');
assert(!rankHtml.includes('2026-10-20'),'Old date belongs only in provenance accordion');
const detailStart=auditSource.indexOf('function detail(g){'),detailEnd=auditSource.indexOf('function paint(',detailStart);
assert(detailStart>=0&&detailEnd>detailStart,'Cannot locate per-sector audit renderer');
const detailRender=new Function('status','esc','amt','fmt','stock',
 auditSource.slice(detailStart,detailEnd)+'\nreturn detail;')(
 ()=>['warn','同日完整逐檔重算'],v=>String(v),v=>String(v),v=>String(v),
 x=>'<div class="test-stock">'+x.code+'</div>');
const group={trade_date:'2026-10-21',aggregate_source_date:'2026-10-20',
 rank_eligible:true,rank_status:'REBUILT_ALL_MEMBERS',rank_amount_100m:133.1,
 verified_count:6,member_count:6,buy_count:5,sell_count:1,flat_count:0,
 stocks:[{code:'2317'}],reconciled:false};
const detailHtml=detailRender(group);
const foldPoint=detailHtml.indexOf('<details class="cms-source-audit" data-cms-source-audit>');
assert(foldPoint>0,'Native collapsed audit details must exist');
assert(detailHtml.indexOf('逐檔資金明細')<detailHtml.indexOf('class="cms-stocks"'),'Stock details remain prominent');
assert(detailHtml.indexOf('class="cms-stocks"')<foldPoint,'Audit is below stock details');
assert(!detailHtml.slice(0,foldPoint).includes('2026-10-20'),'Legacy source date must be hidden until audit expands');
assert(detailHtml.slice(foldPoint).includes('原族群彙總來源日</span><b>2026-10-20</b>'),
 'Source date remains verifiable inside fold');
assert(!/<details class="cms-source-audit"[^>]*\bopen\b/.test(detailHtml),'Audit fold must start closed');
assert(auditSource.includes("e.target.closest?.('.cms-source-audit')")&&auditSource.includes('e.stopPropagation();return;'),
 'Opening audit fold must not accidentally close enclosing group');
assert(auditSource.includes('data-cms-wave-score')&&auditSource.includes("detail:{code,view:'close',closeMode:'swing'}"),
 'Preserve full stock card and Wave Score 2.0 links');
console.log('PASS: old aggregate source date hidden inside collapsible audit; fresh date, coverage, score link and ranking preserved');

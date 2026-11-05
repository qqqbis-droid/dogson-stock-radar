'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const E=require('../../docs/v2/mainforce-core-v1.js');
const run=(name,fn)=>{fn();console.log('PASS mainforce',name)};
const samples=[
 {date:'2026-11-05',code:'2317',name:'樣本',net:-4109,houses:15,c5:-16.8,c20:-22.1,source:'使用者手動提供'},
 {date:'2026-11-04',code:'2317',name:'樣本',net:-11641,houses:14,c5:-17.4,c20:-20.3,source:'使用者手動提供'},
 {date:'2026-11-03',code:'2317',name:'樣本',net:-8529,houses:16,c5:-15.4,c20:-20.2,source:'使用者手動提供'}
];
run('CSV full names, quoted cells and BOM',()=>{
 const text='\uFEFF日期,股票代號,股票名稱,主力買賣超(張),買賣家數差(家),5日集中(%),20日集中(%),資料來源\r\n'+
 '"2026/11/05","2317","範例,測試","-4,109","15","-16.8%","-22.1","籌碼,樣本"\r\n';
 const got=E.importCsv(text,'2026-11-06');
 assert.equal(got.length,1);
 assert.deepEqual([got[0].date,got[0].net,got[0].houses,got[0].c5,got[0].c20],['2026-11-05',-4109,15,-16.8,-22.1]);
 assert.equal(got[0].name,'範例,測試');
 assert.equal(got[0].source,'籌碼,樣本');
});
run('TSV and missing concentration remain null',()=>{
 const text='日期\t股票代號\t主力買賣超\t家數差\n2026-11-05\t2317\t-4109\t15\n';
 const got=E.importCsv(text,'2026-11-06');assert.equal(got[0].c5,null);assert.equal(got[0].c20,null);
 assert.equal(E.summarize(got,'2026-11-05').status,'PARTIAL');
});
run('actual example: 5d easing while 20d deteriorates',()=>{
 const s=E.summarize(samples,'2026-11-05');
 assert.equal(s.status,'SELL_EASING');
 assert.equal(s.d5,0.6);assert.equal(s.d20,-1.8);assert.equal(s.freshness,'SAME_DAY');
 assert.equal(E.summarize(samples,'2026-11-06').freshness,'STALE');
});
run('separate divergence states and no automatic score',()=>{
 assert.equal(E.summarize([{...samples[0],c5:1,c20:-5}], '2026-11-05').status,'RECOVERY_WATCH');
 assert.equal(E.summarize([{...samples[0],c5:3,c20:2}], '2026-11-05').status,'CONCENTRATING');
 assert.ok(!Object.hasOwn(E.summarize(samples,'2026-11-05'),'swing_quality_score'));
});
run('same date import is idempotent and preserves missing columns',()=>{
 const base=E.merge([],samples);
 const incoming=E.importCsv('日期,股票代號,主力買賣超\n2026-11-05,2317,-4000\n','2026-11-06');
 const merged=E.merge(base,incoming);
 assert.equal(merged.length,3);
 assert.equal(merged.find(r=>r.date==='2026-11-05').net,-4000);
 assert.equal(merged.find(r=>r.date==='2026-11-05').c20,-22.1);
 assert.equal(E.merge(merged,incoming).length,3);
});
run('reject fabricated future dates, percentages, invalid rows',()=>{
 assert.throws(()=>E.importCsv('日期,股票代號,5日集中\n2026-11-08,2317,-2\n','2026-11-06'),/未來/);
 assert.throws(()=>E.importCsv('日期,股票代號,5日集中\n2026-11-05,2317,230\n','2026-11-06'),/集中度/);
 assert.throws(()=>E.importCsv('日期,股票代號,5日集中\n2026-11-05,2317,\n','2026-11-06'),/至少需要一項/);
 assert.throws(()=>E.importCsv('日期,股票代號,主力買賣超\n2026-11-05,2317,ABC\n','2026-11-06'),/數值格式/);
 assert.throws(()=>E.importCsv('日期,股票代號,主力買賣超\n11\/05,2317,10\n','2026-11-06'),/西元/);
 assert.throws(()=>E.importCsv('日期,股票代號,主力買賣超\n2026-11-05,2317,10\n2026-11-05,2318,NaN\n','2026-11-06'),/第 3 列/);
});
run('Taipei date stable across Intl localization',()=>{
 const d=E.twDate(new Date('2026-11-05T16:07:00Z'));
 assert.equal(d,'2026-11-06');
});
run('public UI only reads local CSV and public manifest',()=>{
 const root=path.resolve(__dirname,'../../docs/v2');
 const ui=fs.readFileSync(path.join(root,'mainforce-panel-v1.js'),'utf8');
 const index=fs.readFileSync(path.join(root,'index.html'),'utf8');
 for(const must of ['mfManualForm','mfPasteApply','mfFile','mfExport','mfClear','localStorage','SAME_DAY','radar:view-rendered','data-mf-code'])assert.ok(ui.includes(must),must);
 assert.ok(!ui.includes('api.finmind.com')&&!ui.includes('branchTrade')&&!ui.includes('github.com/repos'));
 assert.ok(ui.includes('annotateCards')&&ui.includes('mf-card-evidence')&&ui.includes('radar:cards-rendered'));
 assert.ok(!ui.includes('swing_quality_score =')&&!ui.includes('score = Number('));
 assert.ok(index.includes('mainforce-core-v1.js?v=20261106a'));
 assert.ok(index.includes('mainforce-panel-v1.js?v=20261106b'));
 assert.ok(index.includes('mainforce-panel-v1.css?v=20261106b'));
});
console.log('Mainforce concentration contract tests complete');

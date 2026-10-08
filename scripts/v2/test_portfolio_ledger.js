const fs=require('fs'),vm=require('vm'),path=require('path');
const mem=new Map();
global.localStorage={getItem:k=>mem.has(k)?mem.get(k):null,setItem:(k,v)=>mem.set(k,String(v)),removeItem:k=>mem.delete(k)};
global.document={dispatchEvent:()=>{}};global.CustomEvent=function(type,init){this.type=type;this.detail=init?.detail};global.window={};
const storePath=path.resolve(__dirname,'../../docs/v2/portfolio-store.js');vm.runInThisContext(fs.readFileSync(storePath,'utf8'),{filename:storePath});
const S=window.RadarPortfolioStore,assert=(ok,msg)=>{if(!ok)throw new Error(msg)},near=(a,b)=>Math.abs(Number(a)-Number(b))<1e-9;
localStorage.setItem(S.key,JSON.stringify({schema_version:'1.1.0',positions:[{code:'9999',name:'測試股',shares:40,avg_cost:100,entry_date:'2026-09-01',entry_reason:'首次測試',hold_reason:'原理由',reason_status:'VALID'}]}));
let p=S.get('9999');assert(p.shares===40,'legacy migration shares');assert(near(p.avg_cost,100),'legacy migration avg');assert(p.transaction_count===1,'legacy migration tx count');assert(S.history('9999')[0].action==='OPENING','legacy migration action');
S.addTransaction({code:'9999',name:'測試股',side:'BUY',shares:60,price:110,trade_date:'2026-09-02',reason:'加碼測試'});p=S.get('9999');assert(p.shares===100,'add shares');assert(near(p.avg_cost,106),'weighted avg after add');assert(S.history('9999')[0].action==='ADD','auto ADD action');
S.addTransaction({code:'9999',name:'測試股',side:'SELL',shares:30,price:120,trade_date:'2026-09-03',reason:'減碼測試'});p=S.get('9999');assert(p.shares===70,'reduce shares');assert(near(p.avg_cost,106),'reduce must keep remaining avg cost');assert(near(p.realized_pl,420),'realized pnl after reduce');assert(S.history('9999')[0].action==='REDUCE','auto REDUCE action');
let oversell=false;try{S.addTransaction({code:'9999',side:'SELL',shares:71,price:120,trade_date:'2026-09-03'})}catch{oversell=true}assert(oversell,'oversell must be rejected');
S.addTransaction({code:'9999',name:'測試股',side:'SELL',shares:70,price:90,trade_date:'2026-09-04',reason:'全出'});p=S.get('9999');assert(p.shares===0,'exit shares');assert(near(p.avg_cost,0),'closed position avg resets');assert(near(p.realized_pl,-700),'cumulative realized pnl');assert(S.history('9999')[0].action==='EXIT','auto EXIT action');
S.addTransaction({code:'9999',name:'測試股',side:'BUY',shares:10,price:95,trade_date:'2026-09-05',reason:'第二輪進場'});p=S.get('9999');assert(p.shares===10,'new cycle shares');assert(near(p.avg_cost,95),'new cycle avg');assert(p.cycle_count===2,'new cycle count');assert(S.history('9999')[0].action==='ENTRY','new cycle ENTRY action');
const exported=S.exportData();assert(exported.schema_version==='2.0.0','schema 2.0');assert(Array.isArray(exported.transactions)&&exported.transactions.length===5,'ledger tx persistence');
// A completed cash daytrade is two actual fills saved in one atomic write.
const pre=S.exportData().transactions.length;
let incomplete=false;try{S.addDaytradeRoundTrip({code:'8888',name:'當沖測試',trade_date:'2026-09-08',shares:1000,buy_price:30})}catch{incomplete=true}
assert(incomplete&&S.exportData().transactions.length===pre,'incomplete daytrade must not persist phantom SELL');
const pair=S.addDaytradeRoundTrip({code:'8888',name:'當沖測試',trade_date:'2026-09-08',shares:1000,buy_price:30,sell_price:30.5,reason:'全數已成交'});
const dp=S.get('8888'),dt=S.history('8888');
assert(dp.shares===0&&dp.transaction_count===2,'round trip should close without leftover holdings');
assert(near(dp.realized_pl,500)&&near(pair.gross_profit,500),'gross round-trip pnl');
assert(dt.length===2&&dt.every(x=>x.source==='DAYTRADE_FILL'&&x.daytrade_pair_id===pair.pair_id),'daytrade linked records persist');
assert(dt[0].side==='SELL'&&dt[1].side==='BUY','same-day BUY must sort ahead of SELL');
assert(S.exportData().transactions.length===pre+2,'two actual fills only');
console.log(JSON.stringify({status:'PASS',shares:p.shares,avg_cost:p.avg_cost,realized_pl:p.realized_pl,cycle_count:p.cycle_count,transactions:p.transaction_count}));

const PORTFOLIO_KEY='dogson.portfolio.v1';
const PORTFOLIO_SCHEMA='2.0.0';

function nowIso(){return new Date().toISOString()}
function cleanText(v,max=800){return String(v??'').trim().slice(0,max)}
function cleanCode(v){return cleanText(v,12).toUpperCase().replace(/[^0-9A-Z-]/g,'')}
function cleanNumber(v){const n=Number(v);return Number.isFinite(n)?n:null}
function uid(){return`tx_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,9)}`}
function blank(){return{schema_version:PORTFOLIO_SCHEMA,updated_at:nowIso(),transactions:[],meta:{}}}
function normalizeMeta(p={}){const status=['VALID','WEAKENING','INVALID'].includes(p.reason_status)?p.reason_status:'VALID';return{name:cleanText(p.name,40),hold_reason:cleanText(p.hold_reason||p.note,800),reason_status:status,validation_condition:cleanText(p.validation_condition,800),failure_condition:cleanText(p.failure_condition,800),strategy:cleanText(p.strategy,800),note:cleanText(p.note,800),updated_at:p.updated_at||nowIso()}}
function normalizeTx(t){
  if(!t||typeof t!=='object')return null;
  const code=cleanCode(t.code),side=String(t.side||'').toUpperCase(),shares=cleanNumber(t.shares),price=cleanNumber(t.price??t.avg_cost??t.avg_price);
  if(!code||!['BUY','SELL'].includes(side)||shares==null||shares<=0||!Number.isInteger(shares)||price==null||price<=0)return null;
  const action=['ENTRY','ADD','REDUCE','EXIT','OPENING'].includes(String(t.action||'').toUpperCase())?String(t.action).toUpperCase():(side==='BUY'?'ENTRY':'REDUCE');
  return{id:cleanText(t.id,80)||uid(),code,name:cleanText(t.name,40),side,action,shares:Number(shares),price:Number(price),trade_date:cleanText(t.trade_date||t.entry_date,10),reason:cleanText(t.reason||t.entry_reason,800),note:cleanText(t.note,800),source:cleanText(t.source,60)||'MANUAL_FILL',created_at:t.created_at||nowIso(),updated_at:t.updated_at||nowIso()};
}
function migrateLegacy(x){
  const out=blank();
  for(const p of (x?.positions||[])){
    const code=cleanCode(p?.code),shares=cleanNumber(p?.shares),price=cleanNumber(p?.avg_cost??p?.avg_price);
    if(!code||shares==null||shares<=0||!Number.isInteger(shares)||price==null||price<=0)continue;
    out.transactions.push(normalizeTx({id:`legacy_${code}_${String(p.created_at||p.entry_date||'opening').replace(/[^0-9A-Za-z]/g,'')}`,code,name:p.name,side:'BUY',action:'OPENING',shares,price,trade_date:p.entry_date,reason:p.entry_reason||p.core_reason,note:'由 Portfolio v1 自動轉入；視為期初持倉成交',source:'LEGACY_POSITION_MIGRATION',created_at:p.created_at||nowIso()}));
    out.meta[code]=normalizeMeta(p);
  }
  out.updated_at=x?.updated_at||nowIso();
  return out;
}
function read(){
  try{
    const raw=localStorage.getItem(PORTFOLIO_KEY);if(!raw)return blank();const x=JSON.parse(raw);
    if(x&&Array.isArray(x.transactions)){
      const tx=x.transactions.map(normalizeTx).filter(Boolean),meta={};for(const [k,v] of Object.entries(x.meta||{})){const c=cleanCode(k);if(c)meta[c]=normalizeMeta(v)}
      return{schema_version:PORTFOLIO_SCHEMA,updated_at:x.updated_at||nowIso(),transactions:tx,meta};
    }
    if(x&&Array.isArray(x.positions))return migrateLegacy(x);
    return blank();
  }catch(err){console.warn('portfolio local store read failed',err);return blank()}
}
function write(data){
  const tx=(data.transactions||[]).map(normalizeTx).filter(Boolean),meta={};for(const [k,v] of Object.entries(data.meta||{})){const c=cleanCode(k);if(c)meta[c]=normalizeMeta(v)}
  const out={schema_version:PORTFOLIO_SCHEMA,updated_at:nowIso(),transactions:tx,meta};validateLedger(out);localStorage.setItem(PORTFOLIO_KEY,JSON.stringify(out));
  document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{count:listFrom(out).length,transactions:tx.length}}));return out;
}
function sortedTx(data,code=''){const c=cleanCode(code);return(data.transactions||[]).filter(t=>!c||t.code===c).slice().sort((a,b)=>String(a.trade_date||'').localeCompare(String(b.trade_date||''))||String(a.created_at||'').localeCompare(String(b.created_at||''))||String(a.id).localeCompare(String(b.id)))}
function aggregateCode(data,code){
  const c=cleanCode(code),txs=sortedTx(data,c);let shares=0,avg=0,realized=0,buyValue=0,sellValue=0,cycle=0,lastBuy=null,lastSell=null;
  for(const t of txs){
    const q=Number(t.shares),p=Number(t.price);
    if(t.side==='BUY'){
      if(shares===0)cycle+=1;avg=((avg*shares)+(p*q))/(shares+q);shares+=q;buyValue+=p*q;lastBuy=t;
    }else{
      if(q>shares)throw new Error(`${c} 在 ${t.trade_date||'未填日期'} 的減碼超過當時持股`);realized+=(p-avg)*q;shares-=q;sellValue+=p*q;lastSell=t;if(shares===0)avg=0;
    }
  }
  const m=data.meta?.[c]||{},firstBuy=txs.find(t=>t.side==='BUY');return{code:c,name:m.name||lastBuy?.name||firstBuy?.name||'',shares,avg_cost:shares>0?avg:0,entry_date:firstBuy?.trade_date||'',entry_reason:firstBuy?.reason||'',hold_reason:m.hold_reason||'',reason_status:m.reason_status||'VALID',validation_condition:m.validation_condition||'',failure_condition:m.failure_condition||'',strategy:m.strategy||'',note:m.note||'',realized_pl:realized,buy_value:buyValue,sell_value:sellValue,transaction_count:txs.length,cycle_count:cycle,last_buy:lastBuy,last_sell:lastSell,closed:shares===0&&txs.length>0,created_at:firstBuy?.created_at||'',updated_at:m.updated_at||data.updated_at||nowIso()};
}
function allCodes(data){return[...new Set((data.transactions||[]).map(t=>t.code).filter(Boolean))]}
function listAllFrom(data){return allCodes(data).map(c=>aggregateCode(data,c)).filter(p=>p.transaction_count).sort((a,b)=>String(a.code).localeCompare(String(b.code)))}
function listFrom(data){return listAllFrom(data).filter(p=>p.shares>0)}
function list(){return listFrom(read())}
function listAll(){return listAllFrom(read())}
function get(code){const data=read(),p=aggregateCode(data,code);return p.transaction_count?p:null}
function history(code){return sortedTx(read(),code).slice().reverse()}
function updateMeta(code,patch={}){const c=cleanCode(code);if(!c)throw new Error('股票代號無效');const data=read(),prev=data.meta[c]||{},name=patch.name??prev.name;data.meta[c]=normalizeMeta({...prev,...patch,name});return write(data)}
function addTransaction(input){
  const data=read(),code=cleanCode(input?.code),side=String(input?.side||'').toUpperCase(),shares=cleanNumber(input?.shares),price=cleanNumber(input?.price);
  if(!code||!['BUY','SELL'].includes(side)||shares==null||shares<=0||!Number.isInteger(shares)||price==null||price<=0)throw new Error('成交資料不完整：代號、買賣方向、股數與成交價都必須有效');
  const before=aggregateCode(data,code);if(side==='SELL'&&shares>before.shares)throw new Error(`減碼股數不可超過目前持有 ${before.shares} 股`);
  const action=side==='BUY'?(before.shares>0?'ADD':'ENTRY'):(shares===before.shares?'EXIT':'REDUCE');
  const tx=normalizeTx({...input,code,side,shares,price,action,id:input.id||uid(),source:input.source||'MANUAL_FILL'});data.transactions.push(tx);
  if(input.name||!data.meta[code])data.meta[code]=normalizeMeta({...data.meta[code],name:input.name||data.meta[code]?.name||tx.name});validateLedger(data);write(data);return tx;
}
function deleteTransaction(id){const key=cleanText(id,80),data=read(),before=data.transactions.length;data.transactions=data.transactions.filter(t=>t.id!==key);if(data.transactions.length===before)throw new Error('找不到這筆成交');validateLedger(data);return write(data)}
function upsert(position){
  const code=cleanCode(position?.code);if(!code)throw new Error('股票代號無效');const data=read(),cur=aggregateCode(data,code),shares=cleanNumber(position?.shares),avg=cleanNumber(position?.avg_cost??position?.avg_price);
  if(!cur.transaction_count){if(shares==null||shares<=0||!Number.isInteger(shares)||avg==null||avg<=0)throw new Error('首次持股需要有效股數與成交價');addTransaction({code,name:position.name,side:'BUY',shares,price:avg,trade_date:position.entry_date,reason:position.entry_reason,source:'COMPAT_POSITION_FORM'});}
  else if((shares!=null&&Number(shares)!==cur.shares)||(avg!=null&&Math.abs(Number(avg)-cur.avg_cost)>0.0001))throw new Error('Portfolio Ledger 2.0 請用「新增成交」記錄加碼／減碼，不直接改總股數或平均成本');
  return updateMeta(code,position);
}
function remove(code){const c=cleanCode(code),data=read();data.transactions=data.transactions.filter(t=>t.code!==c);delete data.meta[c];return write(data)}
function clear(){localStorage.removeItem(PORTFOLIO_KEY);document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{count:0,transactions:0}}))}
function exportData(){return read()}
function validateLedger(data){const balances={};for(const t of sortedTx(data)){const c=t.code;balances[c]=balances[c]||0;if(t.side==='BUY')balances[c]+=t.shares;else{if(t.shares>balances[c])throw new Error(`${c} 在 ${t.trade_date||'未填日期'} 的減碼紀錄超過當時持股`);balances[c]-=t.shares}}}
function importData(payload){let data;if(payload&&Array.isArray(payload.transactions)){data={schema_version:PORTFOLIO_SCHEMA,transactions:payload.transactions.map(normalizeTx).filter(Boolean),meta:payload.meta||{}};if(data.transactions.length!==payload.transactions.length)throw new Error('備份中有無效成交紀錄，已停止匯入')}else if(payload&&Array.isArray(payload.positions))data=migrateLegacy(payload);else throw new Error('備份格式不正確');validateLedger(data);return write(data)}
function storageInfo(){return{key:PORTFOLIO_KEY,schema:PORTFOLIO_SCHEMA,scope:'device-local',cloud_sync:false,public_repo:false,model:'transaction-ledger'}}

window.RadarPortfolioStore={key:PORTFOLIO_KEY,schema:PORTFOLIO_SCHEMA,list,listAll,get,history,addTransaction,deleteTransaction,updateMeta,upsert,remove,clear,exportData,importData,storageInfo};

const PORTFOLIO_KEY='dogson.portfolio.v1';
const PORTFOLIO_SCHEMA='1.1.0';

function nowIso(){return new Date().toISOString()}
function cleanText(v,max=800){return String(v??'').trim().slice(0,max)}
function cleanCode(v){return cleanText(v,12).toUpperCase().replace(/[^0-9A-Z-]/g,'')}
function cleanNumber(v){const n=Number(v);return Number.isFinite(n)?n:null}
function blank(){return{schema_version:PORTFOLIO_SCHEMA,updated_at:nowIso(),positions:[]}}
function read(){
  try{
    const raw=localStorage.getItem(PORTFOLIO_KEY);
    if(!raw)return blank();
    const x=JSON.parse(raw);
    if(!x||!Array.isArray(x.positions))return blank();
    return{schema_version:PORTFOLIO_SCHEMA,updated_at:x.updated_at||nowIso(),positions:x.positions.map(normalize).filter(Boolean)};
  }catch(err){console.warn('portfolio local store read failed',err);return blank()}
}
function write(data){
  const out={schema_version:PORTFOLIO_SCHEMA,updated_at:nowIso(),positions:(data.positions||[]).map(normalize).filter(Boolean)};
  localStorage.setItem(PORTFOLIO_KEY,JSON.stringify(out));
  document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{count:out.positions.length}}));
  return out;
}
function normalize(p){
  if(!p||typeof p!=='object')return null;
  const code=cleanCode(p.code),shares=cleanNumber(p.shares),avg=cleanNumber(p.avg_cost??p.avg_price);
  if(!code||shares==null||shares<=0||!Number.isInteger(shares)||avg==null||avg<=0)return null;
  const status=['VALID','WEAKENING','INVALID'].includes(p.reason_status)?p.reason_status:'VALID';
  const legacyCore=cleanText(p.core_reason,600);
  return{
    code,
    name:cleanText(p.name,40),
    shares:Number(shares),
    avg_cost:Number(avg),
    entry_date:cleanText(p.entry_date,10),
    entry_reason:cleanText(p.entry_reason||legacyCore,800),
    hold_reason:cleanText(p.hold_reason||p.note,800),
    reason_status:status,
    validation_condition:cleanText(p.validation_condition,800),
    failure_condition:cleanText(p.failure_condition,800),
    strategy:cleanText(p.strategy,800),
    note:cleanText(p.note,800),
    source:'MANUAL_FILLED_POSITION',
    created_at:p.created_at||nowIso(),
    updated_at:nowIso()
  };
}
function list(){return read().positions.slice().sort((a,b)=>String(a.code).localeCompare(String(b.code)))}
function get(code){const c=cleanCode(code);return list().find(x=>x.code===c)||null}
function upsert(position){
  const data=read(),existing=data.positions.find(x=>x.code===cleanCode(position?.code));
  const p=normalize({...existing,...position,created_at:existing?.created_at});
  if(!p)throw new Error('持股資料不完整：代號、股數與成交均價必須有效；股數可從1股開始');
  const i=data.positions.findIndex(x=>x.code===p.code);
  if(i>=0)data.positions[i]=p;else data.positions.push(p);
  return write(data);
}
function remove(code){const c=cleanCode(code),data=read();data.positions=data.positions.filter(x=>x.code!==c);return write(data)}
function clear(){localStorage.removeItem(PORTFOLIO_KEY);document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{count:0}}))}
function exportData(){return read()}
function importData(payload){
  if(!payload||!Array.isArray(payload.positions))throw new Error('備份格式不正確');
  const positions=payload.positions.map(normalize).filter(Boolean);
  if(payload.positions.length&&positions.length!==payload.positions.length)throw new Error('備份中有無效持股，已停止匯入');
  return write({schema_version:PORTFOLIO_SCHEMA,positions});
}
function storageInfo(){return{key:PORTFOLIO_KEY,schema:PORTFOLIO_SCHEMA,scope:'device-local',cloud_sync:false,public_repo:false}}

window.RadarPortfolioStore={
  key:PORTFOLIO_KEY,
  schema:PORTFOLIO_SCHEMA,
  list,get,upsert,remove,clear,exportData,importData,storageInfo
};

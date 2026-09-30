const PORTFOLIO_KEY='dogson.portfolio.v1';
const PORTFOLIO_SCHEMA='1.0.0';

function nowIso(){return new Date().toISOString()}
function cleanText(v,max=500){return String(v??'').trim().slice(0,max)}
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
  }catch{return blank()}
}
function write(data){
  const out={schema_version:PORTFOLIO_SCHEMA,updated_at:nowIso(),positions:(data.positions||[]).map(normalize).filter(Boolean)};
  localStorage.setItem(PORTFOLIO_KEY,JSON.stringify(out));
  document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{count:out.positions.length}}));
  return out;
}
function normalize(p){
  if(!p||typeof p!=='object')return null;
  const code=cleanCode(p.code),shares=cleanNumber(p.shares),avg=cleanNumber(p.avg_cost);
  if(!code||shares==null||shares<=0||avg==null||avg<=0)return null;
  const status=['UNKNOWN','VALID','WEAKENING','INVALID'].includes(p.reason_status)?p.reason_status:'UNKNOWN';
  return{
    code,
    name:cleanText(p.name,40),
    shares:Math.round(shares),
    avg_cost:Number(avg),
    entry_date:cleanText(p.entry_date,10),
    core_reason:cleanText(p.core_reason,300),
    entry_reason:cleanText(p.entry_reason,600),
    reason_status:status,
    note:cleanText(p.note,600),
    source:'MANUAL_FILLED_POSITION',
    created_at:p.created_at||nowIso(),
    updated_at:nowIso()
  };
}
function list(){return read().positions.slice().sort((a,b)=>String(a.code).localeCompare(String(b.code)))}
function get(code){const c=cleanCode(code);return list().find(x=>x.code===c)||null}
function upsert(position){
  const p=normalize(position);if(!p)throw new Error('持股資料不完整：代號、股數與成交均價必須有效');
  const data=read(),i=data.positions.findIndex(x=>x.code===p.code);
  if(i>=0){p.created_at=data.positions[i].created_at||p.created_at;data.positions[i]=p}else data.positions.push(p);
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

window.RadarPortfolioStore={
  key:PORTFOLIO_KEY,
  schema:PORTFOLIO_SCHEMA,
  list,get,upsert,remove,clear,exportData,importData
};

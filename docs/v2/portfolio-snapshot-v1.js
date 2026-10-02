(()=>{
'use strict';
const state={timer:null,lastKey:'',lastSavedAt:null,error:null};
const cloud=()=>window.INUKOPortfolioCloud;
const store=()=>window.RadarPortfolioStore;
function taipeiDate(){
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const get=t=>parts.find(x=>x.type===t)?.value||'';return `${get('year')}-${get('month')}-${get('day')}`;
}
function ledger(){try{return store()?.exportData?.()||null}catch{return null}}
async function saveSnapshot(reason='sync'){
  const c=cloud(),s=c?.state,client=s?.client,session=s?.session,accountId=s?.accountId;if(!client||!session?.user?.id||!accountId)return false;
  const book=ledger();if(!book)return false;
  const date=taipeiDate(),revision=Number(s.cloudRevision||0),key=`${accountId}:${date}:${revision}`;
  if(reason!=='manual'&&key===state.lastKey)return true;
  const row={account_id:accountId,user_id:session.user.id,snapshot_date:date,schema_version:String(book.schema_version||'2.0.0'),ledger:book,source_revision:revision};
  const {error}=await client.from('inuko_portfolio_snapshots').upsert(row,{onConflict:'account_id,snapshot_date'});
  if(error){state.error=String(error.message||error);console.warn('INUKO daily snapshot failed',error);return false}
  state.lastKey=key;state.lastSavedAt=new Date().toISOString();state.error=null;
  document.dispatchEvent(new CustomEvent('inuko:portfolio-snapshot-saved',{detail:{accountId,date,revision,reason}}));return true;
}
function queue(reason='sync',delay=900){clearTimeout(state.timer);state.timer=setTimeout(()=>saveSnapshot(reason),delay)}
function boot(){
  document.addEventListener('inuko:portfolio-synced',()=>queue('sync',500));
  document.addEventListener('inuko:auth-changed',e=>{if(e.detail?.signedIn)queue('login',1200)});
  document.addEventListener('inuko:portfolio-account-changed',()=>queue('account',1200));
}
window.INUKOPortfolioSnapshots={save:()=>saveSnapshot('manual'),state};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

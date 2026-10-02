(()=>{
'use strict';

const CFG=window.INUKO_CLOUD_CONFIG||{};
const CLOUD_KEY='inuko.cloud.active-account.v1';
const CONFLICT_PREFIX='inuko.cloud.conflict-backup.';
const state={client:null,user:null,accounts:[],activeAccountId:null,revision:0,updatedAt:null,hydrating:false,syncing:false,queued:false,timer:null,lastSyncAt:null,status:'boot',error:null};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const store=()=>window.RadarPortfolioStore;
const configured=()=>Boolean(window.supabase?.createClient&&/^https:\/\//.test(String(CFG.supabaseUrl||''))&&String(CFG.supabaseAnonKey||'').length>20);
const localDate=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const redirectUrl=()=>`${location.origin}${location.pathname}`;

function emit(name='radar:portfolio-cloud-state'){
  document.dispatchEvent(new CustomEvent(name,{detail:snapshot()}));
}
function snapshot(){return{configured:configured(),signedIn:!!state.user,user:state.user?{id:state.user.id,email:state.user.email||''}:null,accounts:state.accounts.map(a=>({id:a.id,name:a.name,kind:a.account_kind})),activeAccountId:state.activeAccountId,revision:state.revision,updatedAt:state.updatedAt,lastSyncAt:state.lastSyncAt,status:state.status,error:state.error};}
function setStatus(status,error=null){state.status=status;state.error=error?String(error.message||error):null;render();emit();}
function activeAccount(){return state.accounts.find(a=>a.id===state.activeAccountId)||null;}
function rememberAccount(){try{if(state.user&&state.activeAccountId)localStorage.setItem(`${CLOUD_KEY}.${state.user.id}`,state.activeAccountId)}catch{}}
function recalledAccount(){try{return state.user?localStorage.getItem(`${CLOUD_KEY}.${state.user.id}`):null}catch{return null}}
function backupConflict(payload){try{localStorage.setItem(`${CONFLICT_PREFIX}${Date.now()}`,JSON.stringify({at:new Date().toISOString(),account_id:state.activeAccountId,revision:state.revision,ledger:payload}))}catch{}}

function ensureStyle(){
  if($('#inukoCloudStyle'))return;
  const s=document.createElement('style');s.id='inukoCloudStyle';s.textContent=`
.inuko-cloud{margin:2px 0 10px;padding:10px 11px;border:1px solid var(--line,#dfe6e1);border-radius:11px;background:var(--soft,#f5f7f4);font-size:.75rem;line-height:1.5}.inuko-cloud-top{display:flex;align-items:center;justify-content:space-between;gap:8px}.inuko-cloud-title{font-weight:900;color:var(--ink,#24352e)}.inuko-cloud-state{font-size:.68rem;color:var(--muted,#718078)}.inuko-cloud-row{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:8px}.inuko-cloud input,.inuko-cloud select{min-height:38px;border:1px solid var(--line,#d9e1dc);border-radius:9px;background:var(--card,#fff);color:var(--ink,#24352e);padding:7px 9px;box-sizing:border-box}.inuko-cloud input[type=email]{flex:1;min-width:190px}.inuko-cloud select{flex:1;min-width:130px}.inuko-cloud button{min-height:36px}.inuko-cloud-note{margin-top:6px;color:var(--muted,#718078);font-size:.68rem}.inuko-cloud-ok{color:#267454}.inuko-cloud-warn{color:#956728}.inuko-cloud-bad{color:#a05245}.inuko-cloud-user{font-weight:700;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:560px){.inuko-cloud-top{align-items:flex-start}.inuko-cloud-row>*{flex:1 1 100%}.inuko-cloud-row button{flex:0 0 auto}.inuko-cloud-user{max-width:160px}}
`;document.head.appendChild(s);
}
function ensureBox(){
  ensureStyle();
  const panel=$('#portfolioPanel');if(!panel)return null;
  let box=$('#inukoCloudBox');
  if(!box){box=document.createElement('div');box.id='inukoCloudBox';box.className='inuko-cloud';const head=panel.querySelector('.section-head');if(head)head.insertAdjacentElement('afterend',box);else panel.prepend(box)}
  return box;
}
function statusLabel(){
  if(!configured())return['尚未連線','inuko-cloud-warn'];
  if(!state.user)return['尚未登入','inuko-cloud-warn'];
  if(state.status==='syncing'||state.status==='loading')return['同步中…',''];
  if(state.status==='conflict')return['同步衝突','inuko-cloud-bad'];
  if(state.status==='error')return['同步失敗','inuko-cloud-bad'];
  if(state.lastSyncAt)return['☁️ 已同步','inuko-cloud-ok'];
  return['已登入','inuko-cloud-ok'];
}
function render(){
  const box=ensureBox();if(!box)return;const [label,klass]=statusLabel();
  const privacy=$('.portfolio-privacy');
  if(!configured()){
    box.innerHTML=`<div class="inuko-cloud-top"><span class="inuko-cloud-title">☁️ INUKO 雲端庫存</span><span class="inuko-cloud-state ${klass}">${label}</span></div><div class="inuko-cloud-note">雲端程式已就位，但尚未填入 Supabase 公開連線設定。設定完成前不會把庫存上傳。</div>`;
    if(privacy)privacy.textContent='🔒 目前仍是本機帳本模式；雲端完成連線後，庫存會綁定登入帳號，不再只依賴這支手機。';return;
  }
  if(!state.user){
    box.innerHTML=`<div class="inuko-cloud-top"><span class="inuko-cloud-title">☁️ INUKO 雲端庫存</span><span class="inuko-cloud-state ${klass}">${label}</span></div><div class="inuko-cloud-row"><input id="inukoCloudEmail" type="email" inputmode="email" autocomplete="email" placeholder="Email"><button id="inukoCloudLogin" class="refresh-btn" type="button">寄登入連結</button></div><div class="inuko-cloud-note">使用 Email Magic Link 登入；不需要建立或保存網站密碼。</div>`;
    if(privacy)privacy.textContent='🔒 尚未登入雲端帳號。目前資料只留在此瀏覽器；登入後才會切換成帳號綁定的雲端帳本。';return;
  }
  const opts=state.accounts.map(a=>`<option value="${esc(a.id)}" ${a.id===state.activeAccountId?'selected':''}>${esc(a.name)}</option>`).join('');
  box.innerHTML=`<div class="inuko-cloud-top"><span class="inuko-cloud-title">☁️ INUKO 雲端庫存</span><span class="inuko-cloud-state ${klass}">${label}</span></div><div class="inuko-cloud-row"><span class="inuko-cloud-user" title="${esc(state.user.email||'')}">${esc(state.user.email||'已登入')}</span><select id="inukoCloudAccount" aria-label="庫存帳戶">${opts}</select><button id="inukoCloudSync" class="text-btn" type="button">立即同步</button><button id="inukoCloudLogout" class="text-btn" type="button">登出</button></div><div class="inuko-cloud-note">${state.lastSyncAt?`最後同步 ${new Date(state.lastSyncAt).toLocaleString('zh-TW')}`:'等待第一次同步'}${state.error?` · ${esc(state.error)}`:''}</div>`;
  if(privacy)privacy.textContent=`🔒 已切換為帳號綁定雲端帳本${activeAccount()?`｜${activeAccount().name}`:''}。庫存資料不寫入公開 GitHub；資料庫以登入者 RLS 權限隔離。`;
}

async function signIn(email){
  if(!configured())throw new Error('Supabase 尚未設定');const e=String(email||'').trim();if(!/^\S+@\S+\.\S+$/.test(e))throw new Error('請輸入有效 Email');
  setStatus('loading');const {error}=await state.client.auth.signInWithOtp({email:e,options:{emailRedirectTo:redirectUrl()}});if(error){setStatus('error',error);throw error}setStatus('magic-link-sent');
}
async function signOut(){if(!state.client)return;await flush();const {error}=await state.client.auth.signOut();if(error)throw error;state.user=null;state.accounts=[];state.activeAccountId=null;state.revision=0;state.updatedAt=null;state.lastSyncAt=null;setStatus('signed-out');}
async function ensureAccounts(){
  setStatus('loading');const {data,error}=await state.client.rpc('inuko_ensure_default_accounts');if(error)throw error;state.accounts=Array.isArray(data)?data:[];
  const remembered=recalledAccount(),preferred=state.accounts.find(a=>a.id===remembered)||state.accounts.find(a=>a.account_kind==='main')||state.accounts[0];state.activeAccountId=preferred?.id||null;rememberAccount();render();
}
async function loadLedger(accountId=state.activeAccountId){
  if(!state.user||!accountId||!store())return;state.hydrating=true;setStatus('loading');
  try{
    const {data,error}=await state.client.from('inuko_portfolio_ledgers').select('ledger,revision,updated_at').eq('account_id',accountId).single();if(error)throw error;
    state.activeAccountId=accountId;state.revision=Number(data?.revision||0);state.updatedAt=data?.updated_at||null;rememberAccount();
    const ledger=data?.ledger&&typeof data.ledger==='object'?data.ledger:{schema_version:'2.0.0',transactions:[],meta:{}};
    store().importData(ledger);state.lastSyncAt=new Date().toISOString();setStatus('ready');
  }finally{state.hydrating=false}
}
async function writeSnapshot(ledger,revision){
  if(!state.user||!state.activeAccountId)return;
  const row={account_id:state.activeAccountId,user_id:state.user.id,snapshot_date:localDate(),schema_version:String(ledger.schema_version||'2.0.0'),ledger,source_revision:revision};
  const {error}=await state.client.from('inuko_portfolio_snapshots').upsert(row,{onConflict:'account_id,snapshot_date'});if(error)console.warn('INUKO snapshot failed',error);
}
async function syncNow(){
  if(!state.user||!state.activeAccountId||!store()||state.hydrating)return;if(state.syncing){state.queued=true;return}
  state.syncing=true;setStatus('syncing');const ledger=store().exportData();const next=state.revision+1;
  try{
    const {data,error}=await state.client.from('inuko_portfolio_ledgers').update({ledger,schema_version:String(ledger.schema_version||'2.0.0'),revision:next}).eq('account_id',state.activeAccountId).eq('revision',state.revision).select('revision,updated_at').maybeSingle();
    if(error)throw error;if(!data){backupConflict(ledger);setStatus('conflict','另一台裝置可能已更新此帳戶；已保留本機衝突備份，請重新載入雲端資料。');return}
    state.revision=Number(data.revision||next);state.updatedAt=data.updated_at||null;state.lastSyncAt=new Date().toISOString();await writeSnapshot(ledger,state.revision);setStatus('ready');
  }catch(err){setStatus('error',err)}finally{state.syncing=false;if(state.queued){state.queued=false;queueSync(200)}}
}
function queueSync(delay=700){if(!state.user||state.hydrating)return;clearTimeout(state.timer);state.timer=setTimeout(syncNow,delay)}
async function flush(){clearTimeout(state.timer);if(state.user&&!state.hydrating)await syncNow()}
async function switchAccount(accountId){
  if(!state.user||accountId===state.activeAccountId)return;await flush();await loadLedger(accountId);document.dispatchEvent(new CustomEvent('radar:portfolio-account-changed',{detail:{accountId}}));
}
async function reloadCloud(){if(!state.user||!state.activeAccountId)return;await loadLedger(state.activeAccountId)}

async function bootCloud(){
  render();if(!configured()){setStatus('unconfigured');return}
  state.client=window.supabase.createClient(CFG.supabaseUrl,CFG.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
  state.client.auth.onAuthStateChange((_event,session)=>{setTimeout(()=>handleSession(session),0)});
  const {data,error}=await state.client.auth.getSession();if(error){setStatus('error',error);return}await handleSession(data?.session||null);
}
let lastUserId=null;
async function handleSession(session){
  const user=session?.user||null;if(!user){lastUserId=null;state.user=null;state.accounts=[];state.activeAccountId=null;state.revision=0;setStatus('signed-out');return}
  if(lastUserId===user.id&&state.accounts.length)return;lastUserId=user.id;state.user=user;
  try{await ensureAccounts();await loadLedger(state.activeAccountId)}catch(err){setStatus('error',err)}
}

function bind(){
  document.addEventListener('radar:portfolio-changed',()=>{if(state.user&&!state.hydrating)queueSync()});
  document.addEventListener('click',async e=>{
    const login=e.target.closest?.('#inukoCloudLogin');if(login){try{login.disabled=true;await signIn($('#inukoCloudEmail')?.value);alert('登入連結已寄出，請到 Email 點開連結。')}catch(err){alert(err.message||'登入失敗')}finally{login.disabled=false}return}
    if(e.target.closest?.('#inukoCloudLogout')){try{await signOut()}catch(err){alert(err.message||'登出失敗')}return}
    if(e.target.closest?.('#inukoCloudSync')){await syncNow();return}
  });
  document.addEventListener('change',async e=>{if(e.target?.id==='inukoCloudAccount'){try{await switchAccount(e.target.value)}catch(err){setStatus('error',err);alert(err.message||'切換帳戶失敗')}}});
  window.addEventListener('pagehide',()=>{if(state.user&&!state.hydrating)queueSync(0)});
}

window.INUKO_PORTFOLIO_CLOUD={configured,snapshot,signIn,signOut,syncNow,reloadCloud,switchAccount,get client(){return state.client}};
bind();if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bootCloud,{once:true});else bootCloud();
})();

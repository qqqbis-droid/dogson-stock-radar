(()=>{
'use strict';
const PROJECT_URL='https://itttysaxjsntjzuonlnf.supabase.co';
const PUBLISHABLE_KEY='sb_publishable_4sR9sM3jVG2A1Z7IJHXH0w_48kV9KZW';
const SCHEMA_VERSION='2.0.0';
const SDK_WAIT_MS=12000;
const state={client:null,session:null,accounts:[],account:null,revision:0,ledger:null,syncing:false,timer:null,dirty:false,status:'local',message:'僅本機'};
const originalSavePortfolioData=typeof savePortfolioData==='function'?savePortfolioData:null;
const originalShowPortfolioEditor=typeof showPortfolioEditor==='function'?showPortfolioEditor:null;
const legacyAtBoot=typeof loadPortfolio==='function'?loadPortfolio():{};
const localHasData=()=>legacyAtBoot&&typeof legacyAtBoot==='object'&&!Array.isArray(legacyAtBoot)&&Object.keys(legacyAtBoot).length>0;
const safePortfolio=x=>x&&typeof x==='object'&&!Array.isArray(x)?x:{};
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const activeKey=uid=>`inuko-active-account:${uid}`;
const cacheKey=(uid,aid)=>`inuko-portfolio-v2:${uid}:${aid}`;
function setMessage(message,status=state.status){state.message=message;state.status=status;renderBar();}
function persistLocal(){
  if(originalSavePortfolioData) originalSavePortfolioData();
  if(state.session&&state.account){
    try{localStorage.setItem(cacheKey(state.session.user.id,state.account.id),JSON.stringify(safePortfolio(portfolioData)))}catch{}
  }
}
function injectStyles(){
 if(document.getElementById('inuko-cloud-style'))return;
 const s=document.createElement('style');s.id='inuko-cloud-style';s.textContent=`
.inuko-cloudbar{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:0 0 12px;padding:9px 10px;border:1px solid #d9dfda;border-radius:14px;background:rgba(255,255,255,.86);color:#31423b;font:700 12px/1.35 -apple-system,BlinkMacSystemFont,"PingFang TC",sans-serif;box-shadow:0 8px 24px rgba(47,68,60,.06)}
.inuko-cloudbar button,.inuko-cloudbar select{border:1px solid #ccd7d1;background:#fff;color:#2d493e;border-radius:10px;padding:7px 9px;font:800 12px/1.2 inherit}.inuko-cloudbar button{cursor:pointer}.inuko-cloudbar .grow{flex:1;min-width:120px}.inuko-cloudbar .ok{color:#1c7657}.inuko-cloudbar .warn{color:#a06a12}.inuko-cloudbar .muted{color:#7e8c86;font-weight:650}.inuko-cloudback{position:fixed;inset:0;z-index:100000;background:rgba(8,14,12,.52);display:flex;align-items:center;justify-content:center;padding:18px}.inuko-cloudmodal{width:min(430px,100%);background:#fff;color:#26362f;border-radius:18px;padding:18px;box-shadow:0 22px 70px rgba(0,0,0,.25);font:700 14px/1.5 -apple-system,BlinkMacSystemFont,"PingFang TC",sans-serif}.inuko-cloudmodal h3{margin:0 0 5px;font-size:19px}.inuko-cloudmodal .sub{color:#75827d;font-size:12px;margin-bottom:14px}.inuko-cloudmodal label{display:block;margin:10px 0 5px;font-size:12px;color:#52635c}.inuko-cloudmodal input{width:100%;border:1px solid #ccd7d1;border-radius:11px;padding:11px 12px;font-size:15px}.inuko-cloudactions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}.inuko-cloudactions button{border:0;border-radius:11px;padding:11px;font-weight:900;cursor:pointer}.inuko-primary{background:#285f4d;color:#fff}.inuko-secondary{background:#edf2ef;color:#345448}.inuko-cloudclose{width:100%;margin-top:8px;border:0;background:transparent;color:#75827d;padding:8px;cursor:pointer}.inuko-cloudnote{margin-top:12px;padding:9px 10px;border-radius:10px;background:#f4f7f5;color:#637069;font-size:11px;line-height:1.55}.inuko-clouderror{margin-top:9px;color:#ad3d4c;font-size:12px;min-height:18px}`;
 document.head.appendChild(s);
}
function installBar(){
 injectStyles();
 if(document.getElementById('inukoCloudBar'))return;
 const bar=document.createElement('div');bar.id='inukoCloudBar';bar.className='inuko-cloudbar';
 const header=document.querySelector('header');
 if(header&&header.parentNode)header.insertAdjacentElement('afterend',bar);else document.body.prepend(bar);
 bar.addEventListener('click',async e=>{
   const login=e.target.closest('[data-inuko-login]');if(login){showAuthModal();return}
   const logout=e.target.closest('[data-inuko-logout]');if(logout&&state.client){await state.client.auth.signOut();return}
   const sync=e.target.closest('[data-inuko-sync]');if(sync){await flushSave(true);return}
 });
 bar.addEventListener('change',async e=>{
   const sel=e.target.closest('[data-inuko-account]');if(!sel)return;
   await flushSave(false);
   await selectAccount(sel.value,false);
 });
 renderBar();
}
function renderBar(){
 const bar=document.getElementById('inukoCloudBar');if(!bar)return;
 if(!state.session){bar.innerHTML=`<span class="grow">☁️ 雲端同步 <span class="muted">${esc(state.message||'僅本機')}</span></span><button type="button" data-inuko-login="1">登入同步</button>`;return}
 const opts=state.accounts.map(a=>`<option value="${esc(a.id)}" ${state.account?.id===a.id?'selected':''}>${esc(a.name)}</option>`).join('');
 const klass=state.status==='saved'||state.status==='ready'?'ok':state.status==='error'||state.status==='conflict'?'warn':'muted';
 bar.innerHTML=`<span>☁️</span><select data-inuko-account="1" aria-label="投資帳戶">${opts}</select><span class="grow ${klass}">${esc(state.message||'已登入')}</span><button type="button" data-inuko-sync="1">立即同步</button><button type="button" data-inuko-logout="1">登出</button>`;
}
function updatePortfolioCopy(){
 const signed=!!state.session;
 document.querySelectorAll('.portfolio-modal .sub').forEach(el=>{if((el.textContent||'').includes('庫存資料'))el.textContent=signed?`目前帳戶：${state.account?.name||'雲端帳戶'}｜已啟用雲端同步`:'庫存資料目前只存在這個瀏覽器'});
 document.querySelectorAll('.portfolio-privacy').forEach(el=>{el.textContent=signed?'🔒 已登入：庫存會同步到你的 Supabase 帳戶，RLS 僅允許本人讀寫；本機仍保留快取供離線顯示。':'🔒 尚未登入：資料只寫入目前裝置的 localStorage；登入後可同步到自己的雲端帳戶。'});
 document.querySelectorAll('.guide-tip').forEach(el=>{if((el.textContent||'').includes('localStorage'))el.textContent=signed?'庫存資料已啟用私人雲端同步；主帳戶與第二帳戶分開保存，本機仍保留快取。':'庫存資料預設保存在目前瀏覽器；登入雲端同步後可跨裝置使用主帳戶／第二帳戶。'});
}
function showAuthModal(){
 document.getElementById('inukoCloudBack')?.remove();
 const back=document.createElement('div');back.id='inukoCloudBack';back.className='inuko-cloudback';
 back.innerHTML=`<div class="inuko-cloudmodal"><h3>☁️ 犬子選股室・雲端同步</h3><div class="sub">登入後可同步主帳戶／第二帳戶、庫存與後續交易流水。</div><label>電子郵件</label><input id="inukoAuthEmail" type="email" inputmode="email" autocomplete="email" placeholder="name@example.com"><label>密碼</label><input id="inukoAuthPassword" type="password" autocomplete="current-password" minlength="8" placeholder="至少 8 碼"><div class="inuko-cloudactions"><button class="inuko-primary" type="button" data-auth-signin="1">登入</button><button class="inuko-secondary" type="button" data-auth-signup="1">建立帳號</button></div><div id="inukoAuthError" class="inuko-clouderror"></div><div class="inuko-cloudnote">前端只使用 Supabase publishable key；不會把 service-role 密鑰放進網站。若新帳號需要信箱確認，完成確認後回到本頁再登入即可。</div><button class="inuko-cloudclose" type="button" data-auth-close="1">取消</button></div>`;
 document.body.appendChild(back);
 const msg=t=>{const x=document.getElementById('inukoAuthError');if(x)x.textContent=t||''};
 back.addEventListener('click',async e=>{
   if(e.target===back||e.target.closest('[data-auth-close]')){back.remove();return}
   const signIn=e.target.closest('[data-auth-signin]'),signUp=e.target.closest('[data-auth-signup]');if(!signIn&&!signUp)return;
   const email=(document.getElementById('inukoAuthEmail')?.value||'').trim();const password=document.getElementById('inukoAuthPassword')?.value||'';
   if(!email||!email.includes('@')){msg('請輸入有效的電子郵件');return}if(password.length<8){msg('密碼至少需要 8 碼');return}
   msg('處理中…');
   try{
     if(signIn){const {error}=await state.client.auth.signInWithPassword({email,password});if(error)throw error;back.remove();}
     else{
       const redirectTo=location.origin+location.pathname;
       const {data,error}=await state.client.auth.signUp({email,password,options:{emailRedirectTo:redirectTo}});if(error)throw error;
       if(data?.session){msg('帳號建立成功，正在登入…');setTimeout(()=>back.remove(),500)}else msg('帳號已建立。請到信箱完成確認，再回來登入。');
     }
   }catch(err){msg(authErrorText(err))}
 });
 setTimeout(()=>document.getElementById('inukoAuthEmail')?.focus(),30);
}
function authErrorText(err){const s=String(err?.message||err||'登入失敗');if(/invalid login credentials/i.test(s))return '帳號或密碼不正確';if(/already registered/i.test(s))return '這個信箱已註冊，請直接登入';if(/rate limit/i.test(s))return '嘗試次數過多，請稍後再試';return s}
async function waitForSdk(){
 const started=Date.now();while(Date.now()-started<SDK_WAIT_MS){if(window.supabase?.createClient)return window.supabase;await new Promise(r=>setTimeout(r,80))}throw new Error('Supabase SDK 載入失敗')
}
async function initClient(){
 try{
   const sdk=await waitForSdk();state.client=sdk.createClient(PROJECT_URL,PUBLISHABLE_KEY,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
   const {data,error}=await state.client.auth.getSession();if(error)throw error;
   await handleSession(data?.session||null);
   state.client.auth.onAuthStateChange((_event,session)=>{setTimeout(()=>{handleSession(session).catch(err=>setMessage(err?.message||'登入狀態更新失敗','error'))},0)});
 }catch(err){setMessage(err?.message||'雲端初始化失敗','error')}
}
async function handleSession(session){
 if(!session){state.session=null;state.accounts=[];state.account=null;state.revision=0;state.ledger=null;setMessage('僅本機','local');updatePortfolioCopy();return}
 state.session=session;setMessage('登入成功，讀取帳戶…','loading');
 const {data,error}=await state.client.rpc('inuko_ensure_default_accounts');if(error)throw error;
 state.accounts=(data||[]).slice().sort((a,b)=>(a.sort_order||0)-(b.sort_order||0));
 if(!state.accounts.length)throw new Error('找不到投資帳戶');
 const remembered=localStorage.getItem(activeKey(session.user.id));
 const preferred=state.accounts.find(a=>a.id===remembered)||state.accounts.find(a=>a.account_kind==='main')||state.accounts[0];
 await selectAccount(preferred.id,true);
 updatePortfolioCopy();
}
async function selectAccount(accountId,allowLegacyMigration){
 const account=state.accounts.find(a=>a.id===accountId)||state.accounts[0];if(!account)return;
 state.account=account;localStorage.setItem(activeKey(state.session.user.id),account.id);setMessage(`讀取 ${account.name}…`,'loading');renderBar();
 const {data,error}=await state.client.from('inuko_portfolio_ledgers').select('account_id,revision,schema_version,ledger,updated_at').eq('account_id',account.id).single();if(error)throw error;
 state.revision=Number(data.revision||0);state.ledger=data.ledger&&typeof data.ledger==='object'?data.ledger:{};state.dirty=false;
 const cloudPortfolio=safePortfolio(state.ledger.portfolio||state.ledger.holdings);
 const shouldMigrate=allowLegacyMigration&&account.account_kind==='main'&&state.revision===0&&Object.keys(cloudPortfolio).length===0&&localHasData();
 if(shouldMigrate){portfolioData=safePortfolio(legacyAtBoot);persistLocal();state.dirty=true;setMessage('正在把原本本機庫存搬上主帳戶…','loading');await flushSave(true);return}
 portfolioData=cloudPortfolio;persistLocal();
 try{localStorage.setItem(cacheKey(state.session.user.id,account.id),JSON.stringify(portfolioData))}catch{}
 setMessage(`${account.name} 已同步 · r${state.revision}`,'ready');if(typeof render==='function')render();updatePortfolioCopy();
}
function scheduleSave(){
 if(!state.session||!state.account)return;state.dirty=true;clearTimeout(state.timer);setMessage('有變更，準備同步…','pending');state.timer=setTimeout(()=>{flushSave(false).catch(err=>setMessage(err?.message||'同步失敗','error'))},650);
}
async function flushSave(manual){
 if(!state.session||!state.account){if(manual)setMessage('尚未登入，資料仍保存在本機','local');return}
 if(state.syncing){if(manual)setMessage('同步進行中…','loading');return}
 if(!manual&&!state.dirty)return;
 clearTimeout(state.timer);state.timer=null;state.syncing=true;setMessage('同步中…','loading');
 try{
   const currentPortfolio=safePortfolio(portfolioData);
   const nextLedger={...(state.ledger||{}),schema_version:SCHEMA_VERSION,portfolio:currentPortfolio,transactions:Array.isArray(state.ledger?.transactions)?state.ledger.transactions:[],meta:{...(state.ledger?.meta||{}),last_client_update:new Date().toISOString(),source:'dogson-stock-radar',account_kind:state.account.account_kind}};
   const {data,error}=await state.client.rpc('inuko_save_portfolio_ledger',{p_account_id:state.account.id,p_expected_revision:state.revision,p_schema_version:SCHEMA_VERSION,p_ledger:nextLedger});if(error)throw error;
   const row=Array.isArray(data)?data[0]:data;
   if(!row?.saved){state.revision=Number(row?.new_revision||state.revision);setMessage('另一裝置已有較新版本，重新載入…','conflict');await selectAccount(state.account.id,false);return}
   state.revision=Number(row.new_revision||state.revision+1);state.ledger=nextLedger;state.dirty=false;persistLocal();
   setMessage(`${state.account.name} 已同步 · r${state.revision}`,'saved');
   Promise.resolve(state.client.rpc('inuko_create_daily_snapshot',{p_account_id:state.account.id})).catch(()=>{});
 }finally{state.syncing=false}
}
function patchPortfolioHooks(){
 if(originalSavePortfolioData){savePortfolioData=function(){persistLocal();scheduleSave()}}
 if(originalShowPortfolioEditor){showPortfolioEditor=function(code){originalShowPortfolioEditor(code);updatePortfolioCopy()}}
}
function boot(){installBar();patchPortfolioHooks();updatePortfolioCopy();initClient()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

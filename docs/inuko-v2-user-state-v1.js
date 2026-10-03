(()=>{
'use strict';
// V2 lightweight safety hotfix. Keep the experimental favorites/autosave helper disabled,
// while fixing password UI and making cloud/local conflict resolution safer.
window.__INUKO_V2_USER_STATE_V1__=true;
if(window.__INUKO_V2_SAFETY_UI_FIX__)return;
window.__INUKO_V2_SAFETY_UI_FIX__=true;

const BACKUP_KEY='inuko.portfolio.safetyBackups.v1';
const MAX_BACKUPS=5;
let scheduled=false;

function cleanLedger(x){
  if(!x||typeof x!=='object')return null;
  return {
    schema_version:String(x.schema_version||'2.0.0'),
    updated_at:x.updated_at||new Date().toISOString(),
    transactions:Array.isArray(x.transactions)?x.transactions:[],
    meta:x.meta&&typeof x.meta==='object'&&!Array.isArray(x.meta)?x.meta:{}
  };
}
function currentLedger(){
  try{return cleanLedger(window.RadarPortfolioStore?.exportData?.())}catch{return null}
}
function canonical(x){
  const v=cleanLedger(x);if(!v)return'';
  const tx=v.transactions.slice().sort((a,b)=>String(a?.id||'').localeCompare(String(b?.id||'')));
  const meta={};for(const k of Object.keys(v.meta).sort())meta[k]=v.meta[k];
  return JSON.stringify({schema_version:v.schema_version,transactions:tx,meta});
}
function loadBackups(){
  try{const v=JSON.parse(localStorage.getItem(BACKUP_KEY)||'[]');return Array.isArray(v)?v:[]}catch{return[]}
}
function writeBackups(items){
  try{localStorage.setItem(BACKUP_KEY,JSON.stringify(items.slice(0,MAX_BACKUPS)))}catch{}
}
function accountId(){
  try{return window.INUKOPortfolioCloud?.accountId?.()||localStorage.getItem('inuko.portfolio.cloud.account')||''}catch{return''}
}
function saveSafetyBackup(reason='change'){
  const ledger=currentLedger();if(!ledger)return null;
  const sig=canonical(ledger);if(!sig)return null;
  const items=loadBackups();
  if(items[0]?.signature===sig)return items[0];
  const item={saved_at:new Date().toISOString(),reason,account_id:accountId(),signature:sig,ledger};
  items.unshift(item);writeBackups(items);return item;
}
function newestRestorableBackup(){
  const now=canonical(currentLedger());
  return loadBackups().find(x=>x?.ledger&&x.signature!==now)||null;
}
function fmtBackupTime(v){
  try{return new Date(v).toLocaleString('zh-TW',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})}catch{return''}
}
function status(text){
  const panel=document.querySelector('#inukoCloudPanel');if(!panel)return;
  let el=panel.querySelector('#inukoSafetyStatus');
  if(!el){el=document.createElement('div');el.id='inukoSafetyStatus';el.className='inuko-cloud-copy';panel.appendChild(el)}
  el.textContent=text||'';
}

function patchPasswordPanel(){
  if(!/\/v2(?:\/|$)/.test(location.pathname))return;
  const panel=document.querySelector('#inukoCloudPanel');
  const form=panel?.querySelector('[data-cloud-set-password]');
  if(!form||form.dataset.inukoPasswordUi==='1')return;
  form.dataset.inukoPasswordUi='1';
  form.style.display='none';

  const actions=document.createElement('div');
  actions.className='inuko-cloud-actions inuko-password-manage';
  const toggle=document.createElement('button');
  toggle.type='button';
  toggle.className='text-btn';
  toggle.textContent='設定／變更登入密碼';
  toggle.setAttribute('aria-expanded','false');
  toggle.addEventListener('click',()=>{
    const opening=form.style.display==='none';
    form.style.display=opening?'':'none';
    toggle.textContent=opening?'收起密碼設定':'設定／變更登入密碼';
    toggle.setAttribute('aria-expanded',opening?'true':'false');
    if(opening)setTimeout(()=>form.querySelector('input[name="password"]')?.focus(),0);
  });
  actions.appendChild(toggle);
  form.parentNode?.insertBefore(actions,form);

  const copy=form.nextElementSibling;
  if(copy?.classList?.contains('inuko-cloud-copy')){
    copy.textContent='已設定過密碼就不用再設定；需要更換密碼時再展開。';
  }
}

function patchConflictPanel(){
  const panel=document.querySelector('#inukoCloudPanel');if(!panel)return;
  const localBtn=panel.querySelector('[data-cloud-keep="local"]');
  const cloudBtn=panel.querySelector('[data-cloud-keep="cloud"]');
  if(localBtn&&cloudBtn){
    localBtn.textContent='保留這台裝置並同步到雲端';
    localBtn.classList.remove('text-btn');
    localBtn.classList.add('refresh-btn');
    localBtn.style.fontWeight='800';

    cloudBtn.textContent='放棄本機變更，改用雲端';
    cloudBtn.classList.remove('refresh-btn');
    cloudBtn.classList.add('text-btn');
    cloudBtn.style.color='#9b3f36';
    cloudBtn.style.borderColor='#d7aaa4';
    cloudBtn.style.background='#fff7f5';

    const actions=localBtn.parentElement;
    if(actions&&actions.firstElementChild!==localBtn)actions.insertBefore(localBtn,cloudBtn);

    const conflict=localBtn.closest('.inuko-cloud-conflict');
    if(conflict&&!conflict.querySelector('.inuko-conflict-safe-copy')){
      const tip=document.createElement('div');
      tip.className='inuko-conflict-safe-copy';
      tip.style.margin='8px 0 2px';
      tip.style.fontWeight='700';
      tip.textContent='剛在這台裝置新增或修改的資料，要保留請選第一個綠色按鈕。只有確定要丟掉本機未同步內容時，才改用雲端。';
      actions?.insertAdjacentElement('beforebegin',tip);
    }
  }
}

function patchRestoreButton(){
  const panel=document.querySelector('#inukoCloudPanel');if(!panel)return;
  const backup=newestRestorableBackup();
  let wrap=panel.querySelector('#inukoSafetyRestore');
  if(!backup){wrap?.remove();return}
  if(!wrap){
    wrap=document.createElement('div');
    wrap.id='inukoSafetyRestore';
    wrap.className='inuko-cloud-actions';
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='text-btn';
    btn.dataset.inukoRestoreBackup='1';
    wrap.appendChild(btn);
    panel.appendChild(wrap);
  }
  const btn=wrap.querySelector('[data-inuko-restore-backup]');
  if(btn){
    btn.textContent=`↩ 復原上一次本機備份（${fmtBackupTime(backup.saved_at)}）`;
    btn.dataset.backupSavedAt=backup.saved_at||'';
  }
}

function patchAll(){
  if(!/\/v2(?:\/|$)/.test(location.pathname))return;
  patchPasswordPanel();
  patchConflictPanel();
  patchRestoreButton();
}
function schedulePatch(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;patchAll()});
}

function installSafetyHandlers(){
  document.addEventListener('click',e=>{
    const localBtn=e.target?.closest?.('[data-cloud-keep="local"]');
    if(localBtn){saveSafetyBackup('before-keep-local');return}

    const cloudBtn=e.target?.closest?.('[data-cloud-keep="cloud"]');
    if(cloudBtn){
      if(cloudBtn.dataset.inukoDangerConfirmed==='1'){
        delete cloudBtn.dataset.inukoDangerConfirmed;
        return;
      }
      e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
      saveSafetyBackup('before-cloud-overwrite');
      const ok=window.confirm('這會用「雲端資料」覆蓋這台裝置目前尚未同步的變更。\n\n系統已先自動備份本機資料。確定仍要改用雲端嗎？');
      if(ok){cloudBtn.dataset.inukoDangerConfirmed='1';setTimeout(()=>cloudBtn.click(),0)}
      else{status('已取消覆蓋；這台裝置的資料沒有被改動。');schedulePatch()}
      return;
    }

    const restore=e.target?.closest?.('[data-inuko-restore-backup]');
    if(restore){
      e.preventDefault();e.stopPropagation();
      const backup=newestRestorableBackup();if(!backup)return;
      const ok=window.confirm(`要復原 ${fmtBackupTime(backup.saved_at)} 的本機備份嗎？\n\n目前資料也會先再備份一份。`);
      if(!ok)return;
      const chosen=backup;
      saveSafetyBackup('before-restore');
      try{
        window.RadarPortfolioStore?.importData?.(chosen.ledger);
        status('已復原本機備份。若畫面再次出現資料衝突，請選「保留這台裝置並同步到雲端」。');
      }catch(err){
        console.error('INUKO safety restore failed',err);
        status('備份復原失敗，原資料未刪除。');
      }
      setTimeout(schedulePatch,50);
    }
  },true);

  document.addEventListener('radar:portfolio-changed',()=>{
    setTimeout(()=>{saveSafetyBackup('portfolio-change');schedulePatch()},0);
  });
  document.addEventListener('submit',e=>{
    if(e.target?.matches?.('[data-cloud-set-password]'))setTimeout(schedulePatch,0);
  },true);
}

function boot(){
  saveSafetyBackup('boot');
  patchAll();
  installSafetyHandlers();
  new MutationObserver(schedulePatch).observe(document.documentElement,{childList:true,subtree:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

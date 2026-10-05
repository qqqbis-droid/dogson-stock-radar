(()=>{
'use strict';
if(window.__INUKO_PORTFOLIO_CLOUD_SAFETY_V2__)return;
window.__INUKO_PORTFOLIO_CLOUD_SAFETY_V2__=true;

const BACKUP_KEY='inuko.portfolio.safetyBackups.v2';
const MAX_BACKUPS=8;
let busy=false,scheduled=false,lastStatus='';

const cloud=()=>window.INUKOPortfolioCloud;
const store=()=>window.RadarPortfolioStore;
function cleanLedger(x){
  if(!x||typeof x!=='object')return null;
  return {
    schema_version:String(x.schema_version||'2.0.0'),
    updated_at:x.updated_at||new Date().toISOString(),
    transactions:Array.isArray(x.transactions)?x.transactions:[],
    meta:x.meta&&typeof x.meta==='object'&&!Array.isArray(x.meta)?x.meta:{}
  };
}
function currentLedger(){try{return cleanLedger(store()?.exportData?.())}catch{return null}}
function canonical(x){
  const v=cleanLedger(x);if(!v)return'';
  const tx=v.transactions.slice().sort((a,b)=>String(a?.id||'').localeCompare(String(b?.id||'')));
  const meta={};for(const k of Object.keys(v.meta).sort())meta[k]=v.meta[k];
  return JSON.stringify({schema_version:v.schema_version,transactions:tx,meta});
}
function loadBackups(){try{const x=JSON.parse(localStorage.getItem(BACKUP_KEY)||'[]');return Array.isArray(x)?x:[]}catch{return[]}}
function writeBackups(xs){try{localStorage.setItem(BACKUP_KEY,JSON.stringify(xs.slice(0,MAX_BACKUPS)))}catch{}}
function accountId(){try{return cloud()?.accountId?.()||localStorage.getItem('inuko.portfolio.cloud.account')||''}catch{return''}}
function saveBackup(reason='change'){
  const ledger=currentLedger(),signature=canonical(ledger);if(!ledger||!signature)return null;
  const xs=loadBackups();if(xs[0]?.signature===signature)return xs[0];
  const item={saved_at:new Date().toISOString(),reason,account_id:accountId(),signature,ledger};
  xs.unshift(item);writeBackups(xs);return item;
}
function newestBackup(){const now=canonical(currentLedger());return loadBackups().find(x=>x?.ledger&&x.signature!==now)||null}
function fmtTime(v){try{return new Date(v).toLocaleString('zh-TW',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})}catch{return''}}
function setStatus(text){
  lastStatus=String(text||'');
  const panel=document.querySelector('#inukoCloudPanel');if(!panel)return;
  let el=panel.querySelector('[data-inuko-cloud-safety-status]');
  if(!el){el=document.createElement('div');el.dataset.inukoCloudSafetyStatus='1';el.className='inuko-cloud-copy';el.style.fontWeight='800';el.style.marginTop='9px';panel.appendChild(el)}
  el.textContent=lastStatus;
}
function ensureStyle(){
  if(document.getElementById('inukoCloudSafetyV2Style'))return;
  const s=document.createElement('style');s.id='inukoCloudSafetyV2Style';s.textContent=`
  .inuko-cloud-safe-tip{margin:8px 0 2px;padding:8px 9px;border-radius:9px;background:#eef8f3;color:#285f4d;font-size:.71rem;line-height:1.5;font-weight:800}
  .inuko-cloud-danger{color:#9b3f36!important;border-color:#d7aaa4!important;background:#fff7f5!important}
  [data-inuko-cloud-safety-status]{padding:7px 8px;border-radius:8px;background:var(--soft)}
  `;document.head.appendChild(s);
}
function patchPanel(){
  ensureStyle();
  const panel=document.querySelector('#inukoCloudPanel');if(!panel)return;
  const c=cloud(),conflict=!!c?.state?.conflict;
  const localBtn=panel.querySelector('[data-cloud-keep="local"]');
  const cloudBtn=panel.querySelector('[data-cloud-keep="cloud"]');
  const syncBtn=panel.querySelector('[data-cloud-sync]');

  if(syncBtn){
    syncBtn.disabled=conflict||busy;
    syncBtn.textContent=conflict?'同步暫停｜先處理差異':busy?'同步中…':'立即同步';
  }
  if(localBtn&&cloudBtn){
    localBtn.textContent=busy?'正在同步這台裝置最新資料…':'保留這台裝置並同步到雲端';
    localBtn.disabled=busy;
    localBtn.classList.remove('text-btn');localBtn.classList.add('refresh-btn');
    cloudBtn.textContent='改用雲端（會先備份本機）';
    cloudBtn.classList.remove('refresh-btn');cloudBtn.classList.add('text-btn','inuko-cloud-danger');
    const actions=localBtn.parentElement;
    if(actions&&actions.firstElementChild!==localBtn)actions.insertBefore(localBtn,cloudBtn);
    const box=localBtn.closest('.inuko-cloud-conflict');
    if(box&&!box.querySelector('.inuko-cloud-safe-tip')){
      const tip=document.createElement('div');tip.className='inuko-cloud-safe-tip';
      tip.textContent='剛新增或修改的成交已先存在這台裝置。要保留最新資料請按綠色按鈕；只有確定要放棄本機未同步內容，才改用雲端。';
      actions?.insertAdjacentElement('beforebegin',tip);
    }
  }

  const backup=newestBackup();
  let wrap=panel.querySelector('[data-inuko-cloud-restore-wrap]');
  if(backup){
    if(!wrap){wrap=document.createElement('div');wrap.dataset.inukoCloudRestoreWrap='1';wrap.className='inuko-cloud-actions';wrap.innerHTML='<button type="button" class="text-btn" data-inuko-cloud-restore>↩ 復原最近本機備份</button>';panel.appendChild(wrap)}
    const btn=wrap.querySelector('[data-inuko-cloud-restore]');if(btn)btn.textContent=`↩ 復原最近本機備份（${fmtTime(backup.saved_at)}）`;
  }else wrap?.remove();
  if(lastStatus)setStatus(lastStatus);
}
function schedulePatch(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;patchPanel()})}

async function keepLatestLocal(){
  if(busy)return;
  const c=cloud();
  if(!c?.state||typeof c.sync!=='function'){
    setStatus('✅ 已儲存在這台裝置；雲端同步尚未就緒，沒有覆蓋任何資料。');return;
  }
  busy=true;saveBackup('before-keep-latest-local');
  // Keep the conflict snapshot current as a second line of defense.
  if(c.state.conflict)c.state.conflict.local=currentLedger();
  // Discard only the stale conflict marker. sync() re-reads RadarPortfolioStore now.
  c.state.conflict=null;
  c.state.message='正在將這台裝置目前最新資料同步到雲端…';
  setStatus('✅ 本機已儲存｜正在同步目前最新資料到雲端…');schedulePatch();
  try{
    await c.sync();
    if(c.state.conflict){
      if(c.state.conflict)c.state.conflict.local=currentLedger();
      setStatus('⚠️ 本機資料仍完整保留；同步期間雲端又有新版本，請再確認一次。');
    }else{
      saveBackup('after-keep-latest-local');
      setStatus('✅ 已儲存在這台裝置，並已同步到雲端。');
    }
  }catch(err){
    console.error('INUKO portfolio safe sync',err);
    setStatus('⚠️ 雲端同步沒有完成，但這台裝置目前資料仍完整保留。');
  }finally{busy=false;setTimeout(schedulePatch,50)}
}

function installHandlers(){
  document.addEventListener('click',e=>{
    const localBtn=e.target?.closest?.('[data-cloud-keep="local"]');
    if(localBtn){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();keepLatestLocal();return}

    const cloudBtn=e.target?.closest?.('[data-cloud-keep="cloud"]');
    if(cloudBtn){
      if(cloudBtn.dataset.inukoSafetyConfirmed==='1'){delete cloudBtn.dataset.inukoSafetyConfirmed;return}
      e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
      saveBackup('before-cloud-overwrite');
      const ok=window.confirm('這會用雲端資料覆蓋這台裝置目前尚未同步的變更。\n\n系統已先備份本機資料。確定要改用雲端嗎？');
      if(ok){cloudBtn.dataset.inukoSafetyConfirmed='1';setTimeout(()=>cloudBtn.click(),0)}
      else setStatus('✅ 已取消覆蓋；這台裝置的資料沒有被改動。');
      setTimeout(schedulePatch,50);return;
    }

    const restore=e.target?.closest?.('[data-inuko-cloud-restore]');
    if(restore){
      e.preventDefault();e.stopPropagation();
      const backup=newestBackup();if(!backup)return;
      if(!window.confirm(`要復原 ${fmtTime(backup.saved_at)} 的本機備份嗎？\n\n目前資料也會先備份一份。`))return;
      saveBackup('before-restore');
      try{
        store()?.importData?.(backup.ledger);
        const c=cloud();if(c?.state?.conflict)c.state.conflict.local=currentLedger();
        setStatus('✅ 已復原本機備份。若仍顯示差異，按「保留這台裝置並同步到雲端」。');
      }catch(err){console.error('INUKO portfolio restore',err);setStatus('⚠️ 備份復原失敗；目前資料沒有被刪除。')}
      setTimeout(schedulePatch,50);
    }
  },true);

  document.addEventListener('radar:portfolio-changed',()=>{
    setTimeout(()=>{
      saveBackup('portfolio-change');
      const c=cloud();
      // Critical race fix: never leave conflict.local pointing at an older local snapshot.
      if(c?.state?.conflict)c.state.conflict.local=currentLedger();
      setStatus(c?.state?.conflict?'✅ 新增／修改已儲存在這台裝置；尚未同步雲端。':'✅ 已儲存在這台裝置；正在同步雲端…');
      schedulePatch();
    },0);
  });
  document.addEventListener('inuko:portfolio-synced',()=>{setStatus('✅ 已儲存在這台裝置，並已同步到雲端。');schedulePatch()});
}
function boot(){
  saveBackup('boot');ensureStyle();installHandlers();patchPanel();
  new MutationObserver(schedulePatch).observe(document.documentElement,{childList:true,subtree:true});
  let tries=0;const wait=setInterval(()=>{tries++;patchPanel();if((cloud()&&document.querySelector('#inukoCloudPanel'))||tries>120)clearInterval(wait)},250);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

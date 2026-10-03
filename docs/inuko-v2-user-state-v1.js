(()=>{
'use strict';
// V2 lightweight UI hotfix. Keep the disabled favorites/autosave helper marker so the
// earlier experimental module cannot run, while fixing the repeated password form.
window.__INUKO_V2_USER_STATE_V1__=true;
if(window.__INUKO_V2_PASSWORD_UI_FIX__)return;
window.__INUKO_V2_PASSWORD_UI_FIX__=true;

let scheduled=false;
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
function schedulePatch(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;patchPasswordPanel()});
}
function boot(){
  patchPasswordPanel();
  new MutationObserver(schedulePatch).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('submit',e=>{
    if(e.target?.matches?.('[data-cloud-set-password]'))setTimeout(schedulePatch,0);
  },true);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

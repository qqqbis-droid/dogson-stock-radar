(()=>{
'use strict';
if(window.__INUKO_V2_USER_STATE_V1__)return;
window.__INUKO_V2_USER_STATE_V1__=true;

const FAVORITES_KEY='inuko.user.favorites.v1';
const DRAFTS_KEY='inuko.user.drafts.v1';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const safeJson=(raw,fallback)=>{try{const x=JSON.parse(raw);return x??fallback}catch{return fallback}};
const cleanCode=v=>String(v||'').trim().toUpperCase().replace(/[^0-9A-Z-]/g,'').slice(0,12);
let favorites=new Set((safeJson(localStorage.getItem(FAVORITES_KEY),'')||[]).map(cleanCode).filter(Boolean));
let drafts=safeJson(localStorage.getItem(DRAFTS_KEY),'')||{};
if(!drafts||typeof drafts!=='object'||Array.isArray(drafts))drafts={};
let favoriteOnly=false;
let remoteUid='';
let remoteHydrating=false;
let remoteTimer=null;
let loadMoreBusy=false;
const formTimers=new WeakMap();

function cloud(){
  const s=window.INUKOPortfolioCloud?.state;
  return s?.client&&s?.session?.user?.id?{client:s.client,uid:s.session.user.id}:null;
}
function saveLocal(){
  localStorage.setItem(FAVORITES_KEY,JSON.stringify([...favorites]));
  localStorage.setItem(DRAFTS_KEY,JSON.stringify(drafts));
}
function mergeDrafts(a,b){
  const out={...a};
  for(const [k,v] of Object.entries(b||{})){
    const av=out[k];
    const at=Date.parse(av?.updated_at||0)||0,bt=Date.parse(v?.updated_at||0)||0;
    if(!av||bt>=at)out[k]=v;
  }
  return out;
}
async function hydrateRemote(){
  const c=cloud();
  if(!c||remoteHydrating||remoteUid===c.uid)return;
  remoteHydrating=true;
  try{
    const {data,error}=await c.client.from('inuko_user_state').select('favorites,drafts,updated_at').eq('user_id',c.uid).maybeSingle();
    if(error)throw error;
    if(data){
      for(const code of data.favorites||[])favorites.add(cleanCode(code));
      drafts=mergeDrafts(drafts,data.drafts||{});
      saveLocal();
    }
    remoteUid=c.uid;
    await pushRemote();
    decorateAll();
  }catch(err){console.warn('INUKO user state hydrate failed',err)}finally{remoteHydrating=false}
}
function queueRemote(){clearTimeout(remoteTimer);remoteTimer=setTimeout(()=>pushRemote().catch(err=>console.warn('INUKO user state sync failed',err)),550)}
async function pushRemote(){
  const c=cloud();if(!c)return;
  const payload={user_id:c.uid,favorites:[...favorites].slice(0,500),drafts,updated_at:new Date().toISOString()};
  const {error}=await c.client.from('inuko_user_state').upsert(payload,{onConflict:'user_id'});if(error)throw error;
}

function draftStatus(form,text){
  let el=form.querySelector('.inuko-draft-status');
  if(!el){el=document.createElement('div');el.className='inuko-draft-status';const actions=form.querySelector('.ledger-actions,.portfolio-dialog-actions');actions?.insertAdjacentElement('beforebegin',el)}
  if(el)el.textContent=text;
}
function formFields(form){
  const out={};
  for(const el of form.elements||[]){if(!el.name||el.type==='file'||el.type==='submit'||el.type==='button')continue;if(el.type==='checkbox'||el.type==='radio'){if(el.checked)out[el.name]=el.value}else out[el.name]=el.value}
  return out;
}
function draftKey(form){
  if(form.id==='ledgerForm')return'ledger';
  if(form.id==='portfolioForm')return'portfolio';
  return'';
}
function saveFormDraft(form){
  const key=draftKey(form);if(!key)return;
  drafts[key]={fields:formFields(form),original_code:cleanCode(form.dataset.originalCode||''),updated_at:new Date().toISOString()};
  saveLocal();queueRemote();
  const t=new Date();draftStatus(form,`✓ 草稿已自動保存 ${t.toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false})}`);
}
function queueFormDraft(form){clearTimeout(formTimers.get(form));formTimers.set(form,setTimeout(()=>saveFormDraft(form),280))}
function clearDraft(key){if(!drafts[key])return;delete drafts[key];saveLocal();queueRemote()}
function restoreDraft(form){
  const key=draftKey(form),d=drafts[key];if(!d?.fields)return;
  const currentCode=cleanCode(form.elements?.code?.value||form.dataset.originalCode||'');
  const draftCode=cleanCode(d.fields.code||d.original_code||'');
  if(currentCode&&draftCode&&currentCode!==draftCode)return;
  let restored=0;
  for(const [name,value] of Object.entries(d.fields)){
    const el=form.elements?.[name];if(!el||el.type==='file'||el.readOnly)continue;
    if((name==='code'||name==='name')&&currentCode&&el.value)continue;
    el.value=value??'';restored++;
  }
  if(restored){
    draftStatus(form,'↩ 已恢復上次未儲存的草稿，繼續輸入即可');
    form.elements?.code?.dispatchEvent(new Event('input',{bubbles:true}));
    form.elements?.side?.dispatchEvent(new Event('change',{bubbles:true}));
  }
}
function watchForms(){
  document.addEventListener('input',e=>{const f=e.target?.closest?.('#ledgerForm,#portfolioForm');if(f)queueFormDraft(f)},true);
  document.addEventListener('change',e=>{const f=e.target?.closest?.('#ledgerForm,#portfolioForm');if(f)queueFormDraft(f)},true);
  document.addEventListener('submit',e=>{
    const f=e.target?.closest?.('#ledgerForm,#portfolioForm');if(!f)return;const key=draftKey(f),dialog=f.closest('dialog');
    setTimeout(()=>{if(dialog&&!dialog.open){clearDraft(key)}},180);
  },true);
  const mo=new MutationObserver(records=>{for(const r of records){if(r.type!=='attributes'||r.attributeName!=='open')continue;const d=r.target;if(!d.open)continue;const f=d.querySelector?.('#ledgerForm,#portfolioForm');if(f)setTimeout(()=>restoreDraft(f),40)}});
  for(const d of document.querySelectorAll('dialog'))mo.observe(d,{attributes:true,attributeFilter:['open']});
  new MutationObserver(rs=>{for(const r of rs)for(const n of r.addedNodes)if(n.nodeType===1){if(n.matches?.('dialog'))mo.observe(n,{attributes:true,attributeFilter:['open']});n.querySelectorAll?.('dialog').forEach(d=>mo.observe(d,{attributes:true,attributeFilter:['open']}))}}).observe(document.body,{childList:true,subtree:true});
}

function codeOf(card){return cleanCode(card?.dataset?.code||card?.dataset?.portfolioCode||card?.querySelector?.('.code')?.textContent?.match(/\b[0-9A-Z-]{3,12}\b/)?.[0]||'')}
function favorite(code){return favorites.has(cleanCode(code))}
function toggleFavorite(code){code=cleanCode(code);if(!code)return;if(favorites.has(code))favorites.delete(code);else favorites.add(code);saveLocal();queueRemote();decorateAll()}
function style(){if($('#inukoUserStateStyle'))return;const s=document.createElement('style');s.id='inukoUserStateStyle';s.textContent=`
.inuko-fav-star{border:0;background:transparent;color:#9aa79f;font-size:1.35rem;line-height:1;padding:4px 5px;cursor:pointer;border-radius:8px;flex:0 0 auto}.inuko-fav-star.on{color:#d6a323}.inuko-fav-star:active{transform:scale(.93)}.inuko-fav-only{min-height:38px;white-space:nowrap}.inuko-fav-only.on{background:#fff4cf;border-color:#e1bd52;color:#6f5310}.inuko-draft-status{font-size:.68rem;color:#658074;padding:3px 1px 5px}.inuko-fav-empty{padding:18px 10px;text-align:center;color:var(--muted);font-size:.78rem}
`;document.head.appendChild(s)}
function ensureFavoriteToggle(){
  const toolbar=$('#radarPanel .toolbar');if(!toolbar||$('#inukoFavoriteOnly'))return;
  const b=document.createElement('button');b.id='inukoFavoriteOnly';b.type='button';b.className='text-btn inuko-fav-only';b.textContent='★ 我的收藏';b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();favoriteOnly=!favoriteOnly;b.classList.toggle('on',favoriteOnly);applyFavoriteFilter(true)});toolbar.appendChild(b);
}
function decorateCard(card){
  const code=codeOf(card);if(!code)return;let b=card.querySelector(':scope > .card-top .inuko-fav-star');if(!b){b=document.createElement('button');b.type='button';b.className='inuko-fav-star';b.setAttribute('aria-label',`收藏 ${code}`);b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();toggleFavorite(code)});const top=card.querySelector(':scope > .card-top');const badge=top?.querySelector('.badge');if(badge)badge.insertAdjacentElement('beforebegin',b);else top?.appendChild(b)}b.classList.toggle('on',favorite(code));b.textContent=favorite(code)?'★':'☆';b.setAttribute('aria-label',favorite(code)?`取消收藏 ${code}`:`收藏 ${code}`)
}
function applyFavoriteFilter(tryLoad=false){
  ensureFavoriteToggle();const btn=$('#inukoFavoriteOnly');if(btn)btn.classList.toggle('on',favoriteOnly);
  const cards=[...document.querySelectorAll('#cards .card[data-code]')];let shown=0;
  for(const card of cards){decorateCard(card);const show=!favoriteOnly||favorite(codeOf(card));card.style.display=show?'':'none';if(show)shown++}
  $('#inukoFavEmpty')?.remove();
  if(favoriteOnly&&tryLoad){const more=$('#loadMore');if(more&&!more.classList.contains('hidden')&&!more.disabled&&!loadMoreBusy){loadMoreBusy=true;more.click();setTimeout(()=>{loadMoreBusy=false;applyFavoriteFilter(false)},350)}}
  if(favoriteOnly&&shown===0&&!loadMoreBusy){const box=$('#cards');if(box){const e=document.createElement('div');e.id='inukoFavEmpty';e.className='inuko-fav-empty';e.textContent=favorites.size?'目前這個分頁沒有收藏股；切到其他分頁仍會保留收藏。':'還沒有收藏股，點股票卡片右上角的 ☆ 就能加入。';box.insertAdjacentElement('afterend',e)}}
  document.querySelectorAll('#portfolioCards .portfolio-card[data-portfolio-code]').forEach(decorateCard);
}
function decorateAll(){style();ensureFavoriteToggle();applyFavoriteFilter(false)}
function watchCards(){
  const mo=new MutationObserver(()=>setTimeout(()=>applyFavoriteFilter(favoriteOnly),20));
  const attach=()=>{const cards=$('#cards'),ports=$('#portfolioCards');if(cards&&!cards.dataset.inukoFavObserved){cards.dataset.inukoFavObserved='1';mo.observe(cards,{childList:true,subtree:true})}if(ports&&!ports.dataset.inukoFavObserved){ports.dataset.inukoFavObserved='1';mo.observe(ports,{childList:true,subtree:true})}};
  attach();new MutationObserver(()=>{attach();decorateAll()}).observe(document.body,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target?.closest?.('.tab'))setTimeout(()=>applyFavoriteFilter(favoriteOnly),100)},true);
  document.addEventListener('radar:view-rendered',()=>setTimeout(()=>applyFavoriteFilter(favoriteOnly),60));
}

function authWatch(){
  const check=()=>{const c=cloud();if(c&&c.uid!==remoteUid)hydrateRemote();if(!c)remoteUid=''};
  document.addEventListener('inuko:auth-changed',()=>setTimeout(check,50));
  setInterval(check,2500);setTimeout(check,350);
}
function boot(){style();watchForms();watchCards();decorateAll();authWatch()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

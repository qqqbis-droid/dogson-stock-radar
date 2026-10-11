(()=>{'use strict';
if(window.RadarFavorites?.version==='2.0')return;
const KEY='inuko.radar.favorites.v2';
const PRIOR=['dogson-favorites-v1','dogson-favorites','dogson-watchlist-v1','dogson-stock-watchlist','inuko-watchlist-v1','dogson.my-watchlist','dogson-radar-watchlist','dogson-stock-radar-favorites','inuko-favorites'];
const clean=v=>{const s=String(v||'').trim();return /^\d{4,6}$/.test(s)?s:''};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const read=(k)=>{try{const v=localStorage.getItem(k);return v?JSON.parse(v):null}catch{return null}};
const toItems=v=>{const list=Array.isArray(v)?v:Array.isArray(v?.favorites)?v.favorites:Array.isArray(v?.watchlist)?v.watchlist:Array.isArray(v?.items)?v.items:Array.isArray(v?.codes)?v.codes:[];return list.map(x=>typeof x==='object'&&x?{code:clean(x.code||x.stock_code||x.symbol),name:String(x.name||x.stock_name||'').slice(0,70)}:{code:clean(x),name:''}).filter(x=>x.code)};
const cache=new Map();let only=false,saving=true;
try{
 const existing=read(KEY),items=toItems(existing);
 items.forEach(x=>cache.set(x.code,x));
 if(!localStorage.getItem(KEY)){
  for(const k of PRIOR)for(const x of toItems(read(k)))if(!cache.has(x.code))cache.set(x.code,x);
  localStorage.setItem(KEY,JSON.stringify([...cache.values()]));
 }
}catch{saving=false}
function store(){if(!saving)return;try{localStorage.setItem(KEY,JSON.stringify([...cache.values()].sort((a,b)=>a.code.localeCompare(b.code))))}catch{saving=false}}
function refreshUi(){
 const saved=cache.size,button=document.getElementById('radarFavoritesOnly');
 if(button){button.textContent=(only?'★ 只看收藏':'☆ 我的收藏')+' '+saved;button.classList.toggle('active',only);button.setAttribute('aria-pressed',String(only));button.title=saving?'收藏存在此瀏覽器，可跨盤中／盤後／當沖查看':'瀏覽器未開放儲存，收藏僅在本次頁面有效'}
 document.querySelectorAll('[data-radar-fav-code]').forEach(btn=>{const yes=cache.has(btn.dataset.radarFavCode);btn.textContent=yes?'★':'☆';btn.classList.toggle('active',yes);btn.setAttribute('aria-pressed',String(yes));btn.setAttribute('aria-label',(yes?'取消收藏 ':'收藏 ')+btn.dataset.radarFavCode)});
 renderMissing();
}
function renderMissing(){
 let tray=document.getElementById('radarFavoritesUnranked');if(!tray)return;
 if(!only||document.querySelector('.tab.active')?.dataset.view==='portfolio'){tray.hidden=true;tray.innerHTML='';return}
 const ranked=new Set([...document.querySelectorAll('#cards .card[data-code]')].map(c=>c.dataset.code));
 const unknown=[...cache.values()].filter(x=>!ranked.has(x.code));
 if(!unknown.length){tray.hidden=true;tray.innerHTML='';return}
 tray.hidden=false;
 tray.innerHTML='<div class="rf-unranked-head">其他收藏 '+unknown.length+' 檔未出現在目前畫面（可能未列入此模式雷達池）</div>'
  +'<div class="rf-unranked-items">'+unknown.slice(0,35).map(x=>'<button type="button" data-radar-fav-search="'+esc(x.code)+'">'+esc(x.code+' '+x.name)+'</button>').join('')+'</div>'
  +'<small>點代號可使用全市場搜尋；這裡不自行產生無來源排名。</small>';
}
function mountFilter(){
 const heading=document.querySelector('#rankingTitle'),wrap=heading?.parentElement;if(!wrap)return;
 let btn=document.getElementById('radarFavoritesOnly');
 if(!btn){
  btn=document.createElement('button');btn.type='button';btn.id='radarFavoritesOnly';btn.className='rf-only';btn.setAttribute('aria-pressed','false');
  wrap.appendChild(btn);
 }
 btn.hidden=document.querySelector('.tab.active')?.dataset.view==='portfolio';
 const panel=document.querySelector('#radarPanel');
 if(panel&&!document.getElementById('radarFavoritesUnranked')){
  const tray=document.createElement('div');tray.id='radarFavoritesUnranked';tray.className='rf-unranked';tray.hidden=true;
  document.getElementById('loadMore')?.insertAdjacentElement('afterend',tray);
 }
 refreshUi();
}
function mountStars(){
 mountFilter();
 document.querySelectorAll('#cards .card[data-code]').forEach(card=>{
  const code=clean(card.dataset.code);if(!code)return;
  const top=card.querySelector(':scope > .card-top');if(!top)return;
  let btn=top.querySelector('[data-radar-fav-code]');
  if(!btn){btn=document.createElement('button');btn.type='button';btn.className='rf-star';btn.dataset.radarFavCode=code;btn.title='收藏／取消收藏';top.insertAdjacentElement('beforeend',btn)}
 });
 refreshUi();
}
function toggle(code,name=''){
 code=clean(code);if(!code)return;
 if(cache.has(code))cache.delete(code);
 else cache.set(code,{code,name:String(name||'').slice(0,70)});
 store();refreshUi();
 document.dispatchEvent(new CustomEvent('radar:favorites-changed',{detail:{code,active:cache.has(code),count:cache.size}}));
}
function setOnly(v,emit=true){
 only=Boolean(v);refreshUi();if(emit)document.dispatchEvent(new CustomEvent('radar:favorites-filter-changed',{detail:{only}}));
}
document.addEventListener('click',e=>{
 const star=e.target.closest('[data-radar-fav-code]');if(star){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
  const card=star.closest('.card'),name=card?.querySelector('.code')?.textContent?.replace(/^\d{4,6}\s*/,'')||'';
  toggle(star.dataset.radarFavCode,name);return}
 if(e.target.closest('#radarFavoritesOnly')){e.preventDefault();e.stopPropagation();setOnly(!only);return}
 const search=e.target.closest('[data-radar-fav-search]');if(search){e.preventDefault();const input=document.querySelector('#searchInput');
  if(input){if(only)setOnly(false);input.value=search.dataset.radarFavSearch;input.dispatchEvent(new Event('input',{bubbles:true}));input.focus()}return}
},true);
document.addEventListener('radar:cards-rendered',mountStars);
document.addEventListener('radar:view-rendered',mountStars);
document.addEventListener('radar:data-reloaded',mountStars);
window.addEventListener('storage',e=>{if(e.key===KEY){cache.clear();toItems(read(KEY)).forEach(x=>cache.set(x.code,x));refreshUi();document.dispatchEvent(new Event('radar:favorites-changed'))}});
window.RadarFavorites={version:'2.0',has:code=>cache.has(clean(code)),only:()=>only,setOnly,toggle,all:()=>[...cache.values()],refresh:mountStars};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mountStars,{once:true});else mountStars();
})();
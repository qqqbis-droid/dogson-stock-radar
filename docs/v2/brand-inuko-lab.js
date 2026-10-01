(()=>{
'use strict';
const BRAND={
  title:'犬子選骨室',
  en:'INUKO LAB',
  tagline:'看盤・找結構・記交易 🦴',
  description:'犬子選骨室｜INUKO LAB：市場環境、族群動能、價格地圖與交易帳本。',
  theme:'#183a30'
};
function meta(name,content,property=false){
  const key=property?'property':'name';
  let el=document.head.querySelector(`meta[${key}="${name}"]`);
  if(!el){el=document.createElement('meta');el.setAttribute(key,name);document.head.appendChild(el)}
  el.setAttribute('content',content);
}
function link(rel,href,attrs={}){
  let el=document.head.querySelector(`link[rel="${rel}"][data-inuko-brand]`);
  if(!el){el=document.createElement('link');el.rel=rel;el.dataset.inukoBrand='1';document.head.appendChild(el)}
  el.href=href;Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));
}
function ensureHead(){
  document.title=`${BRAND.title}｜${BRAND.en}`;
  meta('description',BRAND.description);
  meta('application-name',BRAND.title);
  meta('apple-mobile-web-app-title',BRAND.title);
  meta('theme-color',BRAND.theme);
  meta('og:title',`${BRAND.title}｜${BRAND.en}`,true);
  meta('og:description',BRAND.tagline,true);
  meta('og:type','website',true);
  meta('twitter:card','summary');
  meta('twitter:title',`${BRAND.title}｜${BRAND.en}`);
  meta('twitter:description',BRAND.tagline);
  link('manifest','./manifest.webmanifest?v=20261001-inuko1');
  link('icon','./assets/inuko-lab/mark.svg',{type:'image/svg+xml'});
  link('apple-touch-icon','./assets/inuko-lab/mark.svg');
}
function ensureStyle(){
  if(document.getElementById('inukoLabBrandStyle'))return;
  const s=document.createElement('style');s.id='inukoLabBrandStyle';s.textContent=`
.top .brand{display:flex;align-items:center;gap:9px;font-weight:950;letter-spacing:.01em}.top .brand .inuko-mark{width:30px;height:30px;flex:0 0 30px;border-radius:9px;background:#183a30 url('./assets/inuko-lab/mark.svg') center/cover no-repeat;box-shadow:inset 0 0 0 1px rgba(255,255,255,.14)}.top .brand .inuko-name{display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}.top .brand .inuko-name b{font-size:1.02rem}.top .brand .inuko-name em{font-style:normal;font-size:.66rem;letter-spacing:.11em;color:#a97112;font-weight:900}.top .sub{color:#6f7c75}.top .sub .inuko-tag{color:#88620c;font-weight:800}.inuko-empty-bone{display:inline-flex;align-items:center;gap:4px}
@media(max-width:520px){.top .brand .inuko-mark{width:28px;height:28px;flex-basis:28px}.top .brand .inuko-name b{font-size:.98rem}.top .brand .inuko-name em{font-size:.61rem}.top .sub{font-size:.66rem}}
`;document.head.appendChild(s);
}
function patchAverageCost(){
  document.querySelectorAll('#portfolioDetailBody .portfolio-detail-grid span').forEach(el=>{if(el.textContent.trim()==='成本')el.textContent='平均成本'});
  document.querySelectorAll('#portfolioCards .portfolio-card .muted').forEach(el=>{const t=el.textContent||'';if(/^成本\s/.test(t.trim()))el.textContent=t.replace(/^\s*成本\s+/,'平均成本 ')});
}
function patchBrand(){
  ensureHead();ensureStyle();
  const brand=document.querySelector('.top .brand');if(brand&&!brand.querySelector('.inuko-mark'))brand.innerHTML=`<span class="inuko-mark" aria-hidden="true"></span><span class="inuko-name"><b>${BRAND.title}</b><em>${BRAND.en}</em></span>`;
  const sub=document.querySelector('.top .sub');if(sub)sub.innerHTML=`<span class="inuko-tag">${BRAND.tagline}</span>`;
  const status=document.getElementById('statusBox');if(status&&status.textContent.trim()==='載入中')status.textContent='犬子正在翻資料…';
  document.querySelectorAll('.portfolio-empty p,.muted,.detail-note').forEach(el=>{
    const t=(el.textContent||'').trim();
    if(t==='目前沒有候選' || t==='目前沒有符合條件的候選')el.innerHTML='<span class="inuko-empty-bone">今天沒有值得叼走的骨頭 🦴</span>';
  });
  patchAverageCost();
}
function boot(){patchBrand();const obs=new MutationObserver(()=>patchBrand());obs.observe(document.documentElement,{childList:true,subtree:true});document.addEventListener('radar:portfolio-changed',()=>setTimeout(patchBrand,0));document.addEventListener('radar:view-rendered',()=>setTimeout(patchBrand,0));document.addEventListener('radar:data-reloaded',()=>setTimeout(patchBrand,0));}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

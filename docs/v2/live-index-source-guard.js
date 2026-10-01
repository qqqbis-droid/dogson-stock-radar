(()=>{
'use strict';
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const fmt=(v,d=2)=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const pct=v=>n(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,2)}%`;
const activeView=()=>document.querySelector('.tab.active')?.dataset.view||'intraday';
const tone=v=>n(v)==null?'':Number(v)>0?'live-pulse-rise':Number(v)<0?'live-pulse-fall':'';
async function j(url){const r=await fetch(`${url}${url.includes('?')?'&':'?'}srcguard=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
function pathFor(root,meta){const raw=String(meta?.url||'');return raw.startsWith('./data/')?`${root}/${raw.slice(7)}`:`${root}/${raw.replace(/^\.\//,'')}`}
function td(v){return String(v||'').slice(0,10)}
async function update(){
 const bar=document.getElementById('livePinnedBar');if(!bar)return;
 try{
  const view=activeView(),m=await j('./data/current_manifest.json'),marketKey=(view==='intraday'||view==='daytrade')?'market_intraday_context':'market_close_context',meta=m.datasets?.[marketKey];
  if(!meta)return;
  const [ctx,market,intra]=await Promise.all([j(pathFor('.',meta)),j('../data/market.json').catch(()=>null),j('../data/intraday.json').catch(()=>null)]);
  const target=td(ctx?.trade_date||m.trade_date),isLive=view==='intraday'||view==='daytrade',liveDate=td(intra?.bridge?.trade_date||intra?.trade_date),marketDate=td(market?.trade_date||market?.taiex?.date||market?.otc?.date);
  const liveMap=isLive&&liveDate===target&&intra?.market_intraday&&typeof intra.market_intraday==='object'?intra.market_intraday:{};
  const taLive=liveMap['^TWII']||{},otLive=liveMap['^TWOII']||{};
  const ta=n(taLive.close)!=null?taLive:(marketDate===target?(market?.taiex||{}):{}),ot=n(otLive.close)!=null?otLive:(marketDate===target?(market?.otc||{}):{});
  const tc=n(ta.change_pct)??n(ctx?.components?.taiex?.change_pct),oc=n(ot.change_pct)??n(ctx?.components?.otc?.change_pct),cells=bar.querySelectorAll('.live-pulse-item');
  if(cells[0])cells[0].innerHTML=`<span>加權指數</span><b>${fmt(ta.close,2)}</b><small class="${tone(tc)}">${pct(tc)}</small>`;
  if(cells[1])cells[1].innerHTML=`<span>櫃買指數</span><b>${fmt(ot.close,2)}</b><small class="${tone(oc)}">${pct(oc)}</small>`;
  bar.dataset.indexTradeDate=target||'';
  bar.dataset.indexSource=n(taLive.close)!=null||n(otLive.close)!=null?'MIS_INTRADAY':marketDate===target?'MARKET_SAME_DAY':'NO_SAME_DAY_INDEX';
 }catch(e){console.warn('live index source guard',e)}
}
function boot(){update();setTimeout(update,700);setInterval(update,60000);document.addEventListener('radar:view-rendered',()=>setTimeout(update,80));document.addEventListener('radar:data-reloaded',()=>setTimeout(update,180));document.addEventListener('visibilitychange',()=>{if(!document.hidden)update()});document.addEventListener('click',e=>{if(e.target.closest?.('#livePulseRefresh,#refreshBtn'))setTimeout(update,900)},true)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

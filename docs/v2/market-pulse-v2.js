(()=>{
'use strict';
const S={manifest:null,build:'',cache:new Map(),loading:false};
const $=s=>document.querySelector(s);
const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const fmt=(v,d=2)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const signed=(v,d=2,s='')=>num(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,d)}${s}`;
const pct=v=>num(v)==null?'—':signed(v,2,'%');
const tone=v=>num(v)==null?'':Number(v)>0?'rise':Number(v)<0?'fall':'';
const regime={BROAD_RISK_ON:'全面偏多',SELECTIVE_RISK_ON:'選股偏多',NEUTRAL:'中性',DEFENSIVE:'防守',RISK_OFF:'風險關閉'};
const fresh={LIVE:'即時',FRESH:'盤後',FROZEN:'收盤',STALE:'過期',UNKNOWN:'未知'};
const view=()=>$('.tab.active')?.dataset?.view||'intraday';
function pointChange(x){
  const direct=num(x?.change??x?.change_points??x?.change_value);
  if(direct!=null)return direct;
  const close=num(x?.close),p=num(x?.change_pct);
  if(close==null||p==null||p<=-100)return null;
  const prev=close/(1+p/100);
  return close-prev;
}
function moveText(x){const d=pointChange(x),p=num(x?.change_pct);if(d==null&&p==null)return'—';if(d==null)return pct(p);if(p==null)return signed(d,2,'點');return `${signed(d,2,'點')} · ${pct(p)}`}
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function manifest(force=false){if(S.manifest&&!force)return S.manifest;const m=await json(`./data/current_manifest.json${force?`?pulse=${Date.now()}`:''}`);if(S.build&&S.build!==m.active_build_id)S.cache.clear();S.build=m.active_build_id||'';S.manifest=m;return m}
async function dataset(m,key){const meta=m.datasets?.[key];if(!meta)return null;const ck=`${m.active_build_id}:${key}`;if(S.cache.has(ck))return S.cache.get(ck);const x=await json(meta.url);if(x?.build_id&&x.build_id!==m.active_build_id)throw new Error(`${key} build mismatch`);S.cache.set(ck,x);return x}
function style(){if($('#marketPulseV2Style'))return;const s=document.createElement('style');s.id='marketPulseV2Style';s.textContent=`
#marketPulse{display:none!important}.market-pulse-v2{position:sticky;top:0;z-index:60;display:grid;grid-template-columns:minmax(112px,1.16fr) minmax(104px,1.06fr) minmax(96px,.96fr) auto;gap:5px;align-items:center;min-height:64px;padding:6px 8px;background:#203d35;color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.16)}.market-pulse-v2 .mpv2-cell{min-width:0;padding:4px 5px}.market-pulse-v2 span{display:block;font-size:.61rem;opacity:.72;white-space:nowrap}.market-pulse-v2 b{display:block;margin-top:2px;font-size:.8rem;line-height:1.15;white-space:nowrap;font-variant-numeric:tabular-nums}.market-pulse-v2 small{display:block;margin-top:3px;font-size:.56rem;opacity:.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}.market-pulse-v2 .rise{color:#ffb5ad}.market-pulse-v2 .fall{color:#9fddbd}.market-pulse-v2 button{border:1px solid rgba(255,255,255,.34);background:rgba(255,255,255,.08);color:#fff;border-radius:9px;padding:7px 6px;font-size:.61rem;font-weight:850;white-space:nowrap}.market-pulse-v2 button:disabled{opacity:.5}.top{position:relative!important;top:auto!important}.tabs{top:64px!important;z-index:45!important}@media(max-width:560px){.market-pulse-v2{grid-template-columns:1.13fr 1.05fr .9fr auto;gap:2px;min-height:62px;padding:5px 6px}.market-pulse-v2 .mpv2-cell{padding:3px}.market-pulse-v2 b{font-size:.72rem}.market-pulse-v2 small{font-size:.52rem;letter-spacing:-.01em}.market-pulse-v2 button{padding:7px 5px;font-size:.58rem}.tabs{top:62px!important}}
`;document.head.appendChild(s)}
function ensure(){style();let bar=$('#marketPulseV2');if(bar)return bar;bar=document.createElement('div');bar.id='marketPulseV2';bar.className='market-pulse-v2';bar.setAttribute('aria-label','市場快訊');bar.innerHTML='<div class="mpv2-cell"><span>加權指數</span><b>—</b><small>讀取中</small></div><div class="mpv2-cell"><span>櫃買指數</span><b>—</b><small>讀取中</small></div><div class="mpv2-cell"><span>市場環境</span><b>—</b><small>讀取中</small></div><button id="marketPulseV2Refresh" type="button">更新</button>';$('#app')?.prepend(bar);return bar}
function marketKey(v){return(v==='intraday'||v==='daytrade')?'market_intraday_context':'market_close_context'}
async function render(force=false){if(S.loading)return;S.loading=true;const btn=$('#marketPulseV2Refresh');if(btn)btn.disabled=true;try{const m=await manifest(force),v=view(),[q,ctx]=await Promise.all([dataset(m,'index_quote'),dataset(m,marketKey(v))]);const bar=ensure(),cells=bar.querySelectorAll('.mpv2-cell'),same=String(q?.trade_date||'').slice(0,10)===String(m.trade_date||'').slice(0,10),ta=same?q?.taiex:null,ot=same?q?.otc:null;if(cells[0])cells[0].innerHTML=`<span>加權指數</span><b>${fmt(ta?.close,2)}</b><small class="${tone(ta?.change_pct)}">${moveText(ta)}</small>`;if(cells[1])cells[1].innerHTML=`<span>櫃買指數</span><b>${fmt(ot?.close,2)}</b><small class="${tone(ot?.change_pct)}">${moveText(ot)}</small>`;if(cells[2])cells[2].innerHTML=`<span>市場環境</span><b>${fmt(ctx?.market_score,1)}/15</b><small>${regime[ctx?.market_regime]||ctx?.market_regime||'—'} · ${fresh[ctx?.freshness]||ctx?.freshness||'—'}</small>`;bar.dataset.build=m.active_build_id||'';bar.dataset.tradeDate=m.trade_date||''}catch(err){console.warn('market-pulse-v2',err);const bar=ensure(),cells=bar.querySelectorAll('.mpv2-cell');cells.forEach((c,i)=>{if(i<2)c.querySelector('small')&&(c.querySelector('small').textContent='同日資料暫不可用')})}finally{S.loading=false;if(btn)btn.disabled=false}}
function boot(){ensure();render();document.addEventListener('radar:view-rendered',()=>render());document.addEventListener('radar:data-reloaded',()=>{S.manifest=null;S.cache.clear();render(true)});document.addEventListener('visibilitychange',()=>{if(!document.hidden)render(true)});document.addEventListener('click',e=>{if(e.target.closest?.('#marketPulseV2Refresh')){S.manifest=null;S.cache.clear();render(true)}},true)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();

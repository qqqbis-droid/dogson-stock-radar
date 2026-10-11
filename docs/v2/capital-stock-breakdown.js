(()=>{
'use strict';
if(window.__DOGSON_CAPITAL_MEMBERS_V1__)return;
window.__DOGSON_CAPITAL_MEMBERS_V1__=true;
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const amt=v=>{const n=num(v);if(n==null)return'—';return (n>0?'+':'')+(Math.abs(n)<.01&&n!==0?fmt(n*10000,1)+'萬':fmt(n,2)+'億')};
const lots=v=>num(v)==null?'—':(Number(v)>0?'+':'')+fmt(v,1)+'張';
const verdict={BROAD_INFLOW:'多數個股同步流入',CONCENTRATED_INFLOW:'少數個股主導流入',DIVERGENT_INFLOW:'金額流入、家數分歧',BROAD_OUTFLOW:'多數個股同步流出',SMALL_SAMPLE:'族群成分股樣本較少',MIXED:'多空分歧',UNVERIFIED:'明細尚未完全對帳'};
let cache=null,build='',loading=false,seq=0;
const view=()=>$('.tab.active')?.dataset.view||'intraday';
const active=()=>['close','portfolio'].includes(view());
function style(){
 if($('#dogsonCapitalStocksStyle'))return;
 const s=document.createElement('style');s.id='dogsonCapitalStocksStyle';
 s.textContent="\n#sectorList .capital-chip>.cms-glance {grid-column:1/-1;width:100%;min-width:0;max-width:100%}\n#sectorList .capital-chip>.capital-more>.cms-detail {grid-column:1/-1;width:100%;min-width:0;max-width:100%}\n#sectorList .capital-chip>.capital-more>.capital-member-fallback[hidden] {display:none!important}\n#sectorList .capital-chip>.capital-more>.capital-section-label[hidden],\n#sectorList .capital-chip>.capital-more>.member-list[hidden] {display:none!important}\n.cms-glance {margin:8px 0 2px;padding:9px 10px;background:var(--soft);border:1px solid var(--line);border-radius:10px;line-height:1.5;font-size:.72rem;overflow-wrap:anywhere}\n.cms-glance.good {border-left:3px solid var(--green)}\n.cms-glance.warn {border-left:3px solid #b89636}\n.cms-glance.bad {border-left:3px solid var(--red)}\n.cms-detail {margin-top:10px;padding:12px 0 0;border-top:1px solid var(--line)}\n.cms-title {font-weight:900;font-size:.85rem;line-height:1.4;color:var(--ink,var(--text))}\n.cms-warning {padding:9px 10px;margin:8px 0;border-radius:9px;border:1px solid var(--line);background:var(--soft);font-size:.73rem;line-height:1.55;overflow-wrap:anywhere}\n.cms-stocks {display:grid;grid-template-columns:minmax(0,1fr);gap:9px;max-height:min(650px,76vh);overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;margin-top:11px;width:100%}\n.cms-stock {min-width:0;max-width:100%;padding:11px;border:1px solid var(--line);background:var(--card);border-radius:11px}\n.cms-main {display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0}\n.cms-main button {display:flex;align-items:center;gap:6px;min-width:0;max-width:100%;border:0;background:transparent;color:var(--ink,var(--text));font-weight:850;font-size:.86rem;line-height:1.4;text-align:left;padding:1px 0;cursor:pointer}\n.cms-main .cms-name {min-width:0;overflow-wrap:anywhere}\n.cms-main .cms-arrow {font-size:.75rem;opacity:.75}\n.cms-money {flex:none;font-size:.93rem;font-weight:900;white-space:nowrap;font-variant-numeric:tabular-nums}\n.cms-money.plus {color:var(--red)}\n.cms-money.minus {color:var(--green)}\n.cms-sub {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:8px;color:var(--ink,var(--text))}\n.cms-stat {min-width:0;background:var(--soft);border-radius:8px;padding:7px 8px}\n.cms-stat small {display:block;font-size:.66rem;line-height:1.3;color:var(--muted);font-weight:500}\n.cms-stat b {display:block;font-size:.75rem;line-height:1.35;margin-top:3px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}\n.cms-unverified {font-size:.7rem;line-height:1.5;color:var(--muted);margin-top:7px}\n.cms-method {font-size:.68rem;line-height:1.6;color:var(--muted);margin:10px 0 2px;overflow-wrap:anywhere}\n@media(min-width:760px) {\n  .cms-stocks {grid-template-columns:repeat(2,minmax(0,1fr))}\n}\n@media(max-width:390px) {\n  .cms-main button {font-size:.78rem}\n  .cms-money {font-size:.83rem}\n  .cms-stat b {font-size:.7rem}\n}\n";
 document.head.appendChild(s);
}
function status(g){if(!g.reconciled)return ['bad',verdict.UNVERIFIED];return[g.verdict==='BROAD_INFLOW'?'good':g.verdict==='BROAD_OUTFLOW'?'bad':'warn',verdict[g.verdict]||verdict.MIXED]}
function glance(g){
 const [cls,t]=status(g),count=g.verified_count||0;
 const lead=g.largest_positive_code?' · 最大買超 '+(g.largest_positive_name||g.largest_positive_code)+' '+amt(g.largest_positive_100m):'';
 const div=g.amount_lots_diverge?' · ⚠ 金額／張數背離':'';
 return '<div class="cms-glance '+cls+'" data-cms-glance><b>'+esc(t)+'</b>｜買 '+(g.buy_count||0)+'／'+count+'、賣 '+(g.sell_count||0)+' 檔'+div+'<div>'+esc(lead.replace(/^ · /,''))+' · 有效資料 '+count+'/'+(g.member_count||0)+' 檔</div></div>';
}
function stock(s){
 const n=num(s.estimated_amount_100m);
 const top='<div class="cms-stock"><div class="cms-main"><button type="button" data-stock-code="'+esc(s.code)+'" aria-label="查看 '+esc(s.name)+' 個股詳情"><span class="cms-code">'+esc(s.code)+'</span><span class="cms-name">'+esc(s.name)+'</span><span class="cms-arrow" aria-hidden="true">↗</span></button><strong class="cms-money '+(n>0?'plus':n<0?'minus':'')+'">'+esc(s.valid?amt(n):'待核對')+'</strong></div>';
 if(!s.valid)return top+'<div class="cms-unverified">法人或收盤資料缺漏，日期：外資 '+esc(s.foreign_date||'—')+'／投信 '+esc(s.trust_date||'—')+'</div></div>';
 const items=[['淨買賣',lots(s.net_lots)],['外資',lots(s.foreign_lots)],['投信',lots(s.trust_lots)],['當日收盤',fmt(s.close_price,2)]];
 return top+'<div class="cms-sub">'+items.map(([k,v])=>'<div class="cms-stat"><small>'+esc(k)+'</small><b>'+esc(v)+'</b></div>').join('')+'</div></div>';
}
function detail(g){
 const [,state]=status(g),reconciled=g.reconciled;
 const warn=!reconciled?'<div class="cms-warning">⚠ 明細與族群總額未完全對帳，暫不判斷整個族群強弱。金額差 '+esc(amt(g.delta_amount_100m))+'、張數差 '+esc(lots(g.delta_lots))+'。</div>':'';
 const lead=g.largest_positive_code&&g.largest_positive_share_pct!=null?'<div class="cms-warning">最大買超：'+esc(g.largest_positive_name||g.largest_positive_code)+'，占所有買超個股正向金額 '+esc(fmt(g.largest_positive_share_pct,1))+'%（不是占淨流入）。</div>':'';
 return '<div class="cms-detail" data-cms-detail><div class="cms-title">逐檔資金明細｜'+esc(g.trade_date)+' · '+(g.member_count||0)+' 檔</div>'
 +'<div class="cms-warning">'+esc(state)+'｜買超 '+(g.buy_count||0)+'、賣超 '+(g.sell_count||0)+'、持平 '+(g.flat_count||0)+'；有效驗證 '+(g.verified_count||0)+'／'+(g.member_count||0)+' 檔。</div>'
 +warn+lead+'<div class="cms-stocks">'+((g.stocks||[]).map(stock).join('')||'<div class="cms-warning">沒有可用逐檔資料。</div>')+'</div>'
 +'<p class="cms-method">外資＋投信各股當日淨買賣股數 × 當日收盤價估算；未含自營商。已依估算金額絕對值排序，全部成分股可捲動查看。金額正負不等於族群全體同步買賣。</p></div>';
}
function paint(){
 const host=$('#sectorList');if(!host||!active())return;
 host.querySelectorAll('.capital-chip[data-capital-group]').forEach(card=>{
   const g=cache?.groups?.[card.dataset.capitalGroup];if(!g)return;
   if(card.querySelector('[data-cms-glance]')&&card.querySelector('[data-cms-detail]'))return;
   card.querySelector('[data-cms-glance]')?.remove();card.querySelector('[data-cms-detail]')?.remove();
   const more=card.querySelector('.capital-more');if(!more)return;
   const glanceNode=document.createElement('div');glanceNode.innerHTML=glance(g);
   const h=card.querySelector(':scope > .capital-hint');
   if(h)h.before(glanceNode.firstElementChild);else more.before(glanceNode.firstElementChild);
   more.querySelector('.capital-section-label')?.setAttribute('hidden','');
   more.querySelector('.member-list')?.setAttribute('hidden','');
   more.querySelector('.capital-member-fallback')?.setAttribute('hidden','');
   more.insertAdjacentHTML('beforeend',detail(g));
 });
}
function warning(message){
 const host=$('#sectorList');if(!host||!active())return;
 host.querySelectorAll('.capital-chip[data-capital-group]').forEach(card=>{
  if(card.querySelector('[data-cms-glance]'))return;
  const node=document.createElement('div');node.className='cms-glance warn';node.dataset.cmsGlance='1';
  node.textContent='⚠ '+message;card.querySelector('.capital-more')?.before(node);
 });
}
async function load(){
 if(!active()||loading)return;loading=true;const my=++seq;
 try{
  const m=await fetch('./data/current_manifest.json?t='+Date.now(),{cache:'no-store'}).then(x=>{if(!x.ok)throw Error('manifest '+x.status);return x.json()});
  const meta=m.datasets?.capital_close_members,day=String(m.datasets?.capital_close_context?.as_of||'').slice(0,10);
  if(!meta?.url||!m.active_build_id)throw Error('資料集尚未產生');
  if(build===m.active_build_id&&cache){paint();return}
  const d=await fetch(meta.url,{cache:'no-store'}).then(x=>{if(!x.ok)throw Error('members '+x.status);return x.json()});
  if(d.build_id!==m.active_build_id||d.trade_date!==day)throw Error('資金明細與族群資料日期不一致');
  if(my!==seq)return;cache=d;build=d.build_id;paint();
 }catch(e){console.warn('sector stocks detail',e);warning('逐檔資料尚未取得或資料日不一致，不據此判定族群共振。')}
 finally{loading=false}
}
function sync(){if(!active())return;if(cache)paint();else load()}
function boot(){
 style();const host=$('#sectorList');
 if(host)new MutationObserver(()=>{if(active()){if(cache)paint();else load()}}).observe(host,{childList:true});
 document.addEventListener('radar:view-rendered',()=>setTimeout(sync,150));
 document.addEventListener('radar:data-reloaded',()=>{cache=null;build='';load()});
 document.addEventListener('click',e=>{if(e.target.closest('.tab'))setTimeout(sync,250)});
 sync();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();

const CP6={timer:null};
const cp6num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
function cp6trimNumbers(text){return String(text??'').replace(/-?\d+\.\d+/g,m=>m.replace(/(\.\d*?[1-9])0+$/,'$1').replace(/\.0+$/,''))}
function cp6phrase(text){let s=cp6trimNumbers(text);
  s=s.replace(/明日第一確認點是\s*([^；。]+)[；；]\s*未站穩前不視為突破完成。?/g,'明天先看 $1 能不能站穩；沒站穩就先當作還沒突破。');
  s=s.replace(/明日量能維持並站穩\s*([^，。]+)[，,]\s*才升級為突破確認。?/g,'明天若量能維持、股價站穩 $1，再視為突破確認。');
  s=s.replace(/若先回測\s*([^，。]+)\s*守住後重新轉強[，,]\s*可保留小量試單候選。?/g,'若先回測 $1 能守住，之後再轉強，可續列小量試單候選。');
  s=s.replace(/結構失效參考：\s*確認跌破支撐下緣\s*([^。]+)。?/g,'若確認跌破支撐下緣 $1，原本的多方結構就失效。');
  s=s.replace(/收盤資料可供明日規劃[，,；;]\s*但開盤後仍需重新確認即時量價。?/g,'收盤資料可先做明日規劃，開盤後再確認即時量價。');
  s=s.replace(/盤後僅代表明日候選；現在不可執行，明日仍需重新確認 Trigger 與風險 Gate。?/g,'盤後只是明日候選，現在不用急著動作；明天開盤後再確認觸發條件、量價和風險。');
  s=s.replace(/這是最近完成交易日的收盤定格資料，可用來規劃明日觀察；開盤後仍需重新確認 Trigger、量價與風險 Gate。?/g,'這是最近完成交易日的收盤資料，可先規劃明日觀察；開盤後再確認觸發條件、量價和風險。');
  s=s.replace(/Trigger/g,'觸發條件').replace(/風險 Gate/g,'風險條件');
  return s;
}
function cp6reason(text){let s=cp6trimNumbers(text).trim();
  s=s.replace(/^20日突破$/,'突破20日高點').replace(/^3日突破$/,'突破近3日高點');
  s=s.replace(/^量比\s*([\d.]+)x$/i,(_,x)=>`量能約平常 ${cp6trimNumbers(x)} 倍`);
  s=s.replace(/^距20MA\s*([+-]?[\d.]+%)$/i,(_,x)=>`距20日線 ${cp6trimNumbers(x)}`);
  s=s.replace(/^均線多頭$/,'短中期均線偏多');
  return s;
}
function cp6textNode(el,fn=cp6phrase){if(!el)return;for(const node of [...el.childNodes]){if(node.nodeType===Node.TEXT_NODE){const v=fn(node.nodeValue);if(v!==node.nodeValue)node.nodeValue=v}}}
function cp6cards(){for(const card of document.querySelectorAll('#cards .card[data-code]')){const reason=card.querySelector('.reason');if(reason){const parts=(reason.textContent||'').split('・').map(cp6reason).filter(Boolean);const v=parts.join('・');if(v&&reason.textContent!==v)reason.textContent=v}const blocker=card.querySelector('.blocker');if(blocker){const v=cp6phrase(blocker.textContent||'');if(v!==blocker.textContent)blocker.textContent=v}}}
function cp6detail(){const body=document.getElementById('detailBody');if(!body)return;
  const explains=[...body.querySelectorAll('.score-explain-v4')];if(explains.length>1)explains.slice(1).forEach(x=>x.remove());
  const hero=body.querySelector('.detail-hero p');if(hero){const v=cp6phrase(hero.textContent||'');if(v!==hero.textContent)hero.textContent=v}
  for(const s of body.querySelectorAll('.detail-list span,.zone-note,.component-note,.component-warning,.s4-detail,.s4-summary,.s4-foot')){const v=cp6phrase(s.textContent||'');if(v!==s.textContent)s.textContent=v}
  for(const b of body.querySelectorAll('.evidence-grid b,.evidence-grid small,.zone-card b,.zone-card small,.score-breakdown-block b,.score-breakdown-block span'))cp6textNode(b,cp6trimNumbers);
}
function cp6run(){cp6cards();cp6detail()}
function cp6schedule(delay=60){clearTimeout(CP6.timer);CP6.timer=setTimeout(cp6run,delay)}
new MutationObserver(()=>cp6schedule(50)).observe(document.body,{childList:true,subtree:true});
document.addEventListener('click',e=>{if(e.target.closest?.('.tab')||e.target.closest?.('.card')||e.target.closest?.('#refreshBtn'))cp6schedule(120)},true);
document.addEventListener('DOMContentLoaded',()=>cp6schedule(150));cp6schedule(250);

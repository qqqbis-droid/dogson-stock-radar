#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.26 — 補完 Step 3：庫存決策層。

把原本只有成本／股數／理由的庫存模式，補成：
續抱／只是降溫／暫停加碼／考慮減碼／結構失效。
判讀使用既有 Stage 2.0、5分盤中、60K 20T/60T、日K、相對強弱與振幅狀態；
不新增任何個股總分權重，也不覆寫使用者手動輸入的原始進場理由。
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def must(s,old,new,label,count=1):
    if old not in s: raise SystemExit('v1.5.26 missing marker: '+label)
    return s.replace(old,new,count)

def patch_index():
    p='docs/index.html';s=read(p)
    s=must(s,'Free Edition v1.5.25｜Step 5 多時間框架完整化','Free Edition v1.5.26｜庫存決策層＋多時間框架','header')
    css=r'''
/* v1.5.26 portfolio decision */
.portfolio-decision{margin-top:9px;border:1px solid #34455a;background:#0f1721;border-radius:11px;padding:9px}.portfolio-decision-top{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.portfolio-decision-title{font-size:10px;color:#9ba5b6;font-weight:850}.portfolio-decision-badge{border-radius:999px;padding:5px 8px;font-size:11px;font-weight:900;white-space:nowrap}.portfolio-decision-badge.hold{background:#173527;color:#a5efbf}.portfolio-decision-badge.cool{background:#173049;color:#b7ddff}.portfolio-decision-badge.pause{background:#40300f;color:#ffd477}.portfolio-decision-badge.reduce{background:#43251c;color:#ffc29f}.portfolio-decision-badge.exit{background:#471820;color:#ff9cac}.portfolio-decision-head{font-size:12px;font-weight:900;margin-top:6px}.portfolio-decision-reasons{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.portfolio-decision-reasons span{font-size:9px;background:#151f2a;border:1px solid #2a394a;border-radius:8px;padding:5px 7px;color:#c2ccda}.portfolio-decision-note{font-size:9px;color:var(--muted);line-height:1.45;margin-top:7px}
'''
    if '.portfolio-decision{' not in s:s=must(s,'</style>',css+'\n</style>','portfolio decision css')
    marker='function portfolioHTML(r){'
    fn=r'''function portfolioDecision(r,h){
 const st=stageKey(r?.category),score=+(r?.intraday_score??r?.score??0),amp=String(r?.amplitude_regime||"");
 const mtf=r?.multi_timeframe||{},mstate=String(mtf.state||""),h60=mtf["60m"]||{},daily=mtf.daily||{};
 const rs=r?.relative_multiframe||{},rsState=String(rs.status||"");
 const manual=String(h?.reason_status||"valid");
 const reasons=[];
 const structuralFail=manual==="invalid"||st==="結構失效"||String(h60.state||"")==="DEATH_CROSS"&&String(daily.state||"")==="WEAK";
 if(structuralFail){
  if(manual==="invalid")reasons.push("你已標記原始持有理由消失");
  if(st==="結構失效")reasons.push("Stage 2.0 已進入結構失效");
  if(String(h60.state||"")==="DEATH_CROSS")reasons.push("60K 20T跌破60T");
  if(String(daily.state||"")==="WEAK")reasons.push("日K背景同步偏弱");
  return {key:"exit",label:"❌ 結構失效",head:"原本持有邏輯已出現明顯失效訊號",reasons};
 }
 const multiWeak=mstate==="WEAK"||mstate==="CONFLICT"||h60.bearish===true;
 const relWeak=rsState==="LAGGING";
 if(st==="轉弱警戒"&&(multiWeak||relWeak||score<50)){
  reasons.push("Stage 已轉弱警戒");
  if(multiWeak)reasons.push("60K／日K框架未支持");
  if(relWeak)reasons.push("多時框相對強弱落後市場");
  if(score<50)reasons.push(`盤中動能 ${num(score,0)}/100`);
  return {key:"reduce",label:"🟠 考慮減碼",head:"不是單一雜訊：已有兩層以上轉弱證據",reasons};
 }
 if(st==="轉弱警戒"||multiWeak||relWeak||manual==="weak"){
  if(st==="轉弱警戒")reasons.push("Stage 轉弱，先不要加碼");
  if(multiWeak)reasons.push("60K／日K尚未重新共振");
  if(relWeak)reasons.push("相對市場偏弱");
  if(manual==="weak")reasons.push("你手動標記持有理由轉弱");
  return {key:"pause",label:"⚠️ 暫停加碼",head:"結構尚未正式失效，但先提高警覺",reasons};
 }
 const cooling=st==="回踩承接"||amp==="健康整理"||(mode==="intraday"&&score>0&&score<68&&h60.supportive===true&&String(daily.state||"")!=="WEAK");
 if(cooling){
  if(st==="回踩承接")reasons.push("目前屬發動後回踩承接");
  if(h60.supportive===true)reasons.push(h60.label||"60K結構仍支持");
  if(String(daily.state||"")!=="WEAK")reasons.push("日K主要結構未轉弱");
  if(amp==="健康整理")reasons.push("振幅屬健康整理");
  return {key:"cool",label:"🔵 只是降溫",head:"目前較像整理／回踩，不等於持有理由消失",reasons};
 }
 if(st==="過熱不追"){
  reasons.push("新買點過熱，但持有與追價是兩件事");
  if(h60.supportive===true)reasons.push(h60.label||"60K結構仍在");
  return {key:"hold",label:"✅ 續抱觀察",head:"不適合追高，不代表既有庫存要賣",reasons};
 }
 if(h60.supportive===true)reasons.push(h60.label||"60K 20T/60T支持");
 if(String(daily.state||"")==="BULLISH")reasons.push("日K背景偏多");
 if(rsState==="LEADING"||rsState==="IMPROVING")reasons.push(rs.label||"相對強弱支持");
 if(st)reasons.push(`Stage：${st}`);
 return {key:"hold",label:"✅ 續抱",head:"核心結構仍成立，暫無必要因盤中雜訊退出",reasons:reasons.slice(0,4)};
}
function portfolioDecisionHTML(r,h){
 const d=portfolioDecision(r,h);
 return `<div class="portfolio-decision"><div class="portfolio-decision-top"><div class="portfolio-decision-title">🧭 系統持有判讀</div><span class="portfolio-decision-badge ${d.key}">${d.label}</span></div><div class="portfolio-decision-head">${d.head}</div><div class="portfolio-decision-reasons">${(d.reasons||[]).map(x=>`<span>${escHTML(x)}</span>`).join("")}</div><div class="portfolio-decision-note">這是持有管理層，不把「現在不適合新買」直接解讀成「手上股票要賣」。真正退出仍以你的原始進場理由與結構失效條件為核心。</div></div>`;
}
'''
    if 'function portfolioDecision(r,h)' not in s:s=must(s,marker,fn+marker,'portfolio decision functions')
    old='''<div class="portfolio-reasons"><div class="portfolio-reason"><b>🎯 進場理由</b>${reason(h.entry_reason)}</div>'''
    new='''${portfolioDecisionHTML(r,h)}<div class="portfolio-reasons"><div class="portfolio-reason"><b>🎯 進場理由</b>${reason(h.entry_reason)}</div>'''
    s=must(s,old,new,'insert decision in portfolio')
    s=s.replace('./hourly.js?v=1525','./hourly.js?v=1526').replace('./sw.js?v=1525','./sw.js?v=1526').replace('dogsonSwReloaded1525','dogsonSwReloaded1526')
    write(p,s)

def patch_sw():
    p='docs/sw.js';s=read(p);s=must(s,'dogson-free-v1525','dogson-free-v1526','sw');s=s.replace('./hourly.js?v=1525','./hourly.js?v=1526');write(p,s)

def patch_status():
    p='docs/data/status.json';d=json.loads(read(p));d['version']='1.5.26-free';d['portfolio_mode_version']='1.1';write(p,json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')

if __name__=='__main__':
    patch_index();patch_sw();patch_status();print('v1.5.26 portfolio decision applied')

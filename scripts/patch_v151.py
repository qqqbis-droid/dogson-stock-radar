#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')

def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f'v1.5.1 patch missing marker: {label}')
    return text.replace(old, new, 1)

def patch_build_data():
    p='scripts/build_data.py'
    s=read(p)
    s=s.replace('犬子老師飆股雷達 Free Edition v1.5.0','犬子老師飆股雷達 Free Edition v1.5.1',1)
    s=s.replace('盤中＝執行雷達（即時動能100，籌碼只作背景）；盤後＝波段雷達（延續品質＋進場位置）；大盤15分獨立',
                '盤中＝執行雷達（即時動能100，籌碼只作背景）；盤後＝波段雷達（延續品質直接100分＋進場位置）；大盤15分獨立',1)

    marker='\ndef _close_entry_position_score(r):'
    helper='''\n\ndef _swing_liquidity_score(r):\n    \"\"\"盤後波段延續的流動性 0~10；不和進場位置混在一起。\"\"\"\n    level = str(r.get(\"liquidity_level\") or \"未知\")\n    if level == \"活躍\":\n        return 10.0\n    if level == \"正常\":\n        return 8.0\n    if level == \"偏低\":\n        return 5.0\n    if level == \"不足\":\n        return 0.0\n    return 6.0\n'''
    if '_swing_liquidity_score' not in s:
        if marker not in s:
            raise SystemExit('v1.5.1 missing close entry marker')
        s=s.replace(marker,helper+marker,1)

    old='''        else:\n            # v1.5：盤後是波段雷達。延續品質與進場位置分開，避免『好股票＝現在可追』。\n            stock_raw = float(r.get(\"technical_score\", 0)) + cs + sec + liq_adjust\n            stock_raw = max(0.0, min(85.0, stock_raw))\n            swing = round(stock_raw / 85.0 * 100.0, 1)\n            r[\"stock_raw_score\"] = round(stock_raw, 1)\n            r[\"score\"] = swing\n            r[\"swing_quality_score\"] = swing\n            r[\"swing_continuation_score\"] = swing\n            r[\"entry_position_score\"] = _close_entry_position_score(r)\n            r[\"score_type\"] = \"swing_continuation\"\n            r[\"score_reliable\"] = bool(chip_cov >= 60)\n'''
    new='''        else:\n            # v1.5.1：盤後波段延續直接加總100分，不再先算85再換算。\n            # 技術50＋籌碼25＋族群15＋流動性10＝100；進場位置另外獨立100。\n            tech_component = max(0.0, min(50.0, float(r.get(\"technical_score\") or 0)))\n            chip_component = max(0.0, min(25.0, cs))\n            sector_component = max(0.0, min(15.0, float(sec or 0) * 1.5))\n            liquidity_component = _swing_liquidity_score(r)\n            swing = round(min(100.0, tech_component + chip_component + sector_component + liquidity_component), 1)\n            r[\"swing_components\"] = {\n                \"technical\": round(tech_component, 1),\n                \"chip\": round(chip_component, 1),\n                \"sector\": round(sector_component, 1),\n                \"liquidity\": round(liquidity_component, 1),\n            }\n            r[\"stock_raw_score\"] = swing\n            r[\"score\"] = swing\n            r[\"swing_quality_score\"] = swing\n            r[\"swing_continuation_score\"] = swing\n            r[\"entry_position_score\"] = _close_entry_position_score(r)\n            r[\"score_type\"] = \"swing_continuation_direct_100\"\n            r[\"score_reliable\"] = bool(chip_cov >= 60)\n'''
    s=must_replace(s,old,new,'close direct 100 block')

    old_formula='''\"score_formula\": {\"mode\": \"swing\", \"technical\": 50, \"chip\": 25, \"sector\": 10, \"stock_raw_max\": 85, \"normalized_to\": 100, \"entry_position\": 100, \"market_separate\": 15},'''
    new_formula='''\"score_formula\": {\"mode\": \"swing_direct_100\", \"technical\": 50, \"chip\": 25, \"sector\": 15, \"liquidity\": 10, \"total\": 100, \"normalized\": False, \"entry_position\": 100, \"market_separate\": 15},'''
    s=must_replace(s,old_formula,new_formula,'close score formula')
    s=s.replace('\"version\": \"1.5.0-free\"','\"version\": \"1.5.1-free\"')
    write(p,s)

def patch_index():
    p='docs/index.html'
    s=read(p)
    s=s.replace('Free Edition v1.5.0｜盤中執行雷達＋盤後波段雷達＋可展開族群',
                'Free Edition v1.5.1｜盤中動能100＋盤後波段直接100＋可展開族群',1)
    s=s.replace('<b>階段和品質現在分開看。</b>「剛啟動」主要看突破、量能、VWAP/均線與位階；總分不再是剛啟動的硬門檻。總分 82 代表品質高，不是 82% 會漲。',
                '<b>階段和分數分開看。</b>盤中顯示「盤中動能」，盤後顯示「波段延續」；82分代表條件共振程度，不是82%會漲。「剛啟動」仍主要看突破、量能、VWAP/均線與位階。',1)
    s=s.replace('<b>盤後波段：</b>波段延續＝技術50＋籌碼25＋族群10換算100；另外獨立計算「進場位置100」，避免好股票在過熱位置仍被誤認為好買點。',
                '<b>盤後波段 100：</b>波段延續＝日K技術50＋籌碼25＋族群15＋流動性10，直接加總100，不再用85分換算；另外獨立計算「進場位置100」，避免好股票在過熱位置仍被誤認為好買點。',1)
    s=s.replace('<b>族群 10：</b>改用多因子共振：廣度3＋強度2＋量能2＋領頭股2＋延續性1。強勢股成交金額占比也納入強度，避免冷門小股一起紅就拿高分；點開族群即可點選共振個股。',
                '<b>族群共振原始10：</b>廣度3＋強度2＋量能2＋領頭股2＋延續性1；盤中換算為20分、盤後換算為15分。強勢股成交金額占比也納入強度；點開族群即可點選共振個股。',1)

    old_close=''' return `<div class=\"parts closeparts\">\n  <div class=\"part\"><div class=\"partv\">${num(r.technical_score,0)}/50</div><div class=\"partl\">日K技術</div></div>\n  <div class=\"part\"><div class=\"partv\">${(+r.chip_coverage_pct||0)<60?\"待補\":num(r.chip_score,0)+\"/25\"}</div><div class=\"partl\">籌碼${(+r.chip_coverage_pct||0)<60?\" · 資料不足\":\"\"}</div></div>\n  <div class=\"part\"><div class=\"partv\">${num(r.sector_score,1)}/10</div><div class=\"partl\">族群延續</div></div>\n  <div class=\"part\"><div class=\"partv\">${num(r.entry_position_score,0)}/100</div><div class=\"partl\">進場位置</div></div>\n </div>`;'''
    new_close=''' const sw=r.swing_components||{};\n return `<div class=\"parts closeparts\">\n  <div class=\"part\"><div class=\"partv\">${num(sw.technical??r.technical_score,0)}/50</div><div class=\"partl\">日K技術</div></div>\n  <div class=\"part\"><div class=\"partv\">${(+r.chip_coverage_pct||0)<60?\"待補\":num(sw.chip??r.chip_score,0)+\"/25\"}</div><div class=\"partl\">籌碼${(+r.chip_coverage_pct||0)<60?\" · 資料不足\":\"\"}</div></div>\n  <div class=\"part\"><div class=\"partv\">${num(sw.sector??((r.sector_score||0)*1.5),1)}/15</div><div class=\"partl\">族群延續</div></div>\n  <div class=\"part\"><div class=\"partv\">${num(sw.liquidity,0)}/10</div><div class=\"partl\">流動性</div></div>\n  <div class=\"part\"><div class=\"partv\">${num(r.entry_position_score,0)}/100</div><div class=\"partl\">進場位置 · 獨立</div></div>\n </div>`;'''
    s=must_replace(s,old_close,new_close,'close parts UI')

    old_footer='<div class="footer">階段看價格行為｜個股品質 = 技術50＋籌碼25＋族群10（85換算100）｜大盤15分獨立判斷操作環境</div>'
    new_footer='<div class="footer" id="footerText">盤中動能100＝價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10｜籌碼只作背景｜大盤15分獨立</div>'
    s=must_replace(s,old_footer,new_footer,'mode footer')

    anchor='''function qualityCls(q){return q===\"高共振\"?\"high\":q===\"強\"?\"strong\":\"\"}\n'''
    replacement='''function qualityCls(q){return (q===\"高共振\"||q===\"高延續\"||q===\"強動能\")?\"high\":(q===\"強\"||q===\"轉強\")?\"strong\":\"\"}\nfunction updateFooter(){\n const el=$(\"footerText\");if(!el)return;\n el.textContent=mode===\"intraday\"\n  ?\"盤中動能100＝價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10｜籌碼只作背景｜大盤15分獨立\"\n  :\"波段延續100＝日K技術50＋籌碼25＋族群15＋流動性10｜直接加總不換算｜進場位置100獨立｜大盤15分獨立\";\n}\n'''
    s=must_replace(s,anchor,replacement,'footer helper')

    old_tab='''$(\"marketbox\").innerHTML=marketHTML();$(\"rotationbox\").innerHTML=rotationHTML();render()});'''
    new_tab='''$(\"marketbox\").innerHTML=marketHTML();$(\"rotationbox\").innerHTML=rotationHTML();updateFooter();render()});'''
    s=must_replace(s,old_tab,new_tab,'tab footer refresh')
    s=s.replace('realtime-config.js?v=150','realtime-config.js?v=151')
    s=s.replace('realtime.js?v=150','realtime.js?v=151')
    write(p,s)

def patch_sw():
    p='docs/sw.js'
    s=read(p)
    s=s.replace("const CACHE='dogson-free-v150';","const CACHE='dogson-free-v151';",1)
    s=s.replace('realtime-config.js?v=150','realtime-config.js?v=151')
    s=s.replace('realtime.js?v=150','realtime.js?v=151')
    write(p,s)

def main():
    patch_build_data()
    patch_index()
    patch_sw()
    print('v1.5.1 patch applied')

if __name__=='__main__':
    main()

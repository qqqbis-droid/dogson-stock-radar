#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.16 — rewrite help for first-time users without changing scoring logic."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/index.html"
SW = ROOT / "docs/sw.js"

s = INDEX.read_text(encoding="utf-8")

# Friendly help styles.
style_marker = '.helptext{color:#cbd3df;font-size:12px;line-height:1.65;margin-top:10px}.helptext b{color:white}'
style_add = style_marker + '.guide-intro{background:#0e131a;border:1px solid #29313e;border-radius:11px;padding:10px 11px}.guide-title{font-size:14px;font-weight:900;color:#b9ddff;margin:16px 0 7px}.guide-card{background:#10151d;border:1px solid #252d39;border-radius:11px;padding:10px 11px;margin:7px 0}.guide-line{margin:5px 0}.guide-key{color:#fff;font-weight:850}.guide-formula{margin-top:7px;color:#98a5b7;font-size:11px;line-height:1.55}.guide-tip{margin-top:8px;padding:7px 9px;border-left:3px solid #4d8ac7;background:#111923;color:#d9e8f8}.guide-warn{color:#ffd477}.guide-mini{color:#9ba5b6;font-size:11px}'
if style_marker not in s:
    raise SystemExit("help style marker missing")
s = s.replace(style_marker, style_add, 1)

new_help = r'''<details class="help">
   <summary>❓ 每個數值怎麼看？第一次使用請點我</summary>
   <div class="helptext">
    <div class="guide-intro"><b>先記住一件事：高分不等於「一定會漲」。</b><br>這個雷達是把「大盤環境、族群強弱、個股條件、現在的位置」整理在一起，幫你快速比較。第一次使用時，建議照 <b>大盤 → 族群 → 個股 → 位置</b> 的順序看，不要只盯著單一分數。</div>

    <div class="guide-title">① 先選對模式：盤中還是盤後？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">⚡ 盤中雷達</span>：看「現在正在變強的是誰」。適合交易時間觀察動能、族群輪動、突破與回踩。</div>
      <div class="guide-line"><span class="guide-key">🌙 盤後雷達</span>：看「收盤後，這檔股票適不適合繼續追蹤成波段」。會加入日K、籌碼、法人與進場位置。</div>
      <div class="guide-tip">同一檔股票盤中分數高、盤後分數普通，不代表資料打架；兩套雷達看的時間尺度不同。</div>
    </div>

    <div class="guide-title">② 先看大盤 15 分：今天適合積極還是保守？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">大盤 15 分</span>是「市場環境分」，和個股 100 分分開計算。</div>
      <div class="guide-line">分數越高，代表加權、櫃買、市場廣度與資金環境越配合多方；分數越低，代表個股就算很強，也要更注意大盤拖累。</div>
      <div class="guide-line"><span class="guide-key">盤中</span>主要看今天即時的加權、櫃買、上漲家數、資金動能與族群擴散。</div>
      <div class="guide-line"><span class="guide-key">盤後</span>再加入收盤後的趨勢與官方外資方向。</div>
      <div class="guide-tip">簡單用法：先決定今天要不要積極，再去挑個股，不要反過來只因為看到一檔高分股就忽略市場。</div>
    </div>

    <div class="guide-title">③ 盤中動能 100 分：這檔股票「現在」有多強？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">盤中動能 /100</span>：分數越高，代表當下價格、量能、相對市場、族群與交易品質越同步。</div>
      <div class="guide-line"><span class="guide-key">價格結構 30</span>：有沒有站在重要位置上、突破後能不能守住。</div>
      <div class="guide-line"><span class="guide-key">量價／動能 25</span>：成交量有沒有跟上，漲勢是不是有效推進，而不是只突然抽一下。</div>
      <div class="guide-line"><span class="guide-key">相對強弱 15</span>：這檔股票有沒有比它所屬市場更強。</div>
      <div class="guide-line"><span class="guide-key">族群 20</span>：是不是同族群一起動，而不是只有單兵上漲。</div>
      <div class="guide-line"><span class="guide-key">流動性／追價風險 10</span>：股票是否好進出，以及現在會不會已經太熱、太容易追高。</div>
      <div class="guide-formula">盤中籌碼只當背景，不放進這 100 分。100 分＝30＋25＋15＋20＋10。</div>
    </div>

    <div class="guide-title">④ 盤中常見數值，白話怎麼看？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">相對加權／相對櫃買</span>：個股漲跌幅減掉市場漲跌幅。例：個股 +3%、加權 +1%，就是「相對加權 +2%」。正數越大，代表越跑贏市場。</div>
      <div class="guide-line"><span class="guide-key">VWAP</span>：今天市場的平均成交成本。股價站在 VWAP 上方通常較強；離 VWAP 太遠則要小心追高。</div>
      <div class="guide-line"><span class="guide-key">距 VWAP</span>：現價離 VWAP 幾%。正值＝在上方；負值＝在下方。</div>
      <div class="guide-line"><span class="guide-key">同時間量速</span>：今天到現在的成交量，和過去同一時間相比有多快。1.0x 約等於平常；1.5～3x 代表明顯活躍；太高也可能過熱。</div>
      <div class="guide-line"><span class="guide-key">今日振幅</span>：今天最高到最低一共走了多大範圍。振幅大不一定好，要看價格最後停在哪裡。</div>
      <div class="guide-line"><span class="guide-key">區間位置</span>：現價位於今日高低區間的哪裡。越接近 100%，代表越靠近今日高點；越接近 0%，代表越靠近低點。</div>
      <div class="guide-line"><span class="guide-key">振幅效率</span>：今天走出來的振幅，有多少真的轉成上漲。高振幅但效率差，常代表震盪很大卻沒有有效推進。</div>
      <div class="guide-line"><span class="guide-key">同時段振幅倍數</span>：今天此刻的振幅，是過去同時間平均的幾倍。用來辨認今天是不是異常活躍。</div>
      <div class="guide-formula">相對強弱評分：相對市場 ≥+2% 得 10 分；+1～&lt;+2% 得 8 分；+0.3～&lt;+1% 得 6 分；0～&lt;+0.3% 得 4 分；-1～&lt;0% 得 2 分；≤-1% 得 0 分。若同時站上 VWAP 且近 15 分鐘仍上漲，再加 5 分，最高 15 分。</div>
    </div>

    <div class="guide-title">⑤ 盤中族群成交資金輪動：現在市場注意力往哪裡？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">吸金熱度</span>不是法人淨買超金額，而是看「成交金額占比有沒有增加」，再搭配族群漲跌、站上 VWAP 的比例、上漲家數與量速。</div>
      <div class="guide-line"><span class="guide-key">吸金前 3</span>：目前市場成交資金明顯往這些族群集中。</div>
      <div class="guide-line"><span class="guide-key">降溫前 3</span>：成交資金占比與價格結構正在轉弱。</div>
      <div class="guide-line">可以先展開整個輪動區，再展開單一族群；點成分股就會打開個股小卡。</div>
      <div class="guide-tip">盤中回答的是「現在市場在炒哪裡」；盤後法人資金流回答的是「外資＋投信今天把錢放在哪裡」。兩者本來就可能不同。</div>
    </div>

    <div class="guide-title">⑥ 族群共振：這檔股票是不是有人一起走？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">族群共振 /10</span>：看同族群上漲家數、強度、量能、領頭股與延續性。</div>
      <div class="guide-line">分數高代表「不是只有這一檔在動」，通常比單兵上漲更有參考價值。</div>
      <div class="guide-line">盤中把族群共振換算成 20 分；盤後換算成 15 分。</div>
      <div class="guide-line">如果沒有自訂細族群，系統會改用官方產業當作代理群組，仍可展開看同產業股票。</div>
      <div class="guide-formula">原始 10 分＝廣度 3＋強度 2＋量能 2＋領頭股 2＋延續性 1。</div>
    </div>

    <div class="guide-title">⑦ 盤後波段延續 100 分：收盤後還值得繼續追蹤嗎？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">波段延續 /100</span>：用來看這檔股票目前的日K趨勢、籌碼、族群與流動性是否仍支持波段。</div>
      <div class="guide-line"><span class="guide-key">日K技術 50</span>：均線、趨勢、突破、強弱與量價結構。</div>
      <div class="guide-line"><span class="guide-key">籌碼 25</span>：外資、投信、借券、融資等是否配合。</div>
      <div class="guide-line"><span class="guide-key">族群 15</span>：同族群是否仍有共振。</div>
      <div class="guide-line"><span class="guide-key">流動性 10</span>：成交金額是否足夠、是否容易進出。</div>
      <div class="guide-formula">波段延續 100＝日K技術 50＋籌碼 25＋族群 15＋流動性 10。</div>
    </div>

    <div class="guide-title">⑧ 「波段延續」和「進場位置」一定要分開看</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">波段延續高</span>：代表股票本身條件好、趨勢仍有延續性。</div>
      <div class="guide-line"><span class="guide-key">進場位置高</span>：代表目前價格位置相對比較適合觀察進場，不是已經拉得很遠。</div>
      <div class="guide-line"><span class="guide-warn">常見情況：</span>好股票也可能已經漲太多。這時「波段延續」可以很高，但「進場位置」不一定漂亮。</div>
      <div class="guide-tip">想找波段，不要只找最高分；要找「延續性好，而且位置沒有太差」的股票。</div>
    </div>

    <div class="guide-title">⑨ 籌碼欄位怎麼看？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">外資連 3 買</span>：外資是否連續三個交易日站在買方。</div>
      <div class="guide-line"><span class="guide-key">借券連 3 減</span>：借券賣出是否連續下降。通常代表放空壓力沒有繼續增加，但不能單獨當買進理由。</div>
      <div class="guide-line"><span class="guide-key">投信</span>：顯示最近交易日投信淨買賣方向。</div>
      <div class="guide-line"><span class="guide-key">融資</span>：觀察散戶槓桿是否快速增加；股價漲、融資暴增時要特別注意追高風險。</div>
      <div class="guide-line">盤中籌碼只當背景；盤後才正式放進波段延續評分。</div>
    </div>

    <div class="guide-title">⑩ 盤後族群法人資金流：法人今天買哪個族群？</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">今日估算流入 TOP 3／流出 TOP 3</span>：依今天「外資＋投信」估算淨買賣金額排序。</div>
      <div class="guide-line"><span class="guide-key">今日</span>看今天力度；<span class="guide-key">5 日</span>看短線是否持續；<span class="guide-key">20 日</span>看較長一段時間是否累積。</div>
      <div class="guide-line">金額算法是「外資＋投信淨買賣股數 × 當日收盤價」，再把同族群加總。</div>
      <div class="guide-line"><span class="guide-warn">注意：</span>這是估算金額，不是法人每一筆實際成交價，因此用來比較「力度」最合適。</div>
      <div class="guide-line">展開族群後可以看到成分股，再點個股開啟小卡。</div>
    </div>

    <div class="guide-title">⑪ 盤後其他常見數值</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">日量比</span>：今天成交量 ÷ 20 日平均量。1.0x 約等於平常；高於 1 代表今天比平常熱。</div>
      <div class="guide-line"><span class="guide-key">距 20MA</span>：股價離 20 日均線多遠。正數代表在均線上；太高代表可能已經拉太遠。</div>
      <div class="guide-line"><span class="guide-key">5 日／20 日漲幅</span>：最近一週／約一個月的價格變化，用來快速看短中期位階。</div>
      <div class="guide-line"><span class="guide-key">RSI</span>：看近期強弱與過熱程度。55～72 常屬強勢區；非常高時要留意過熱，不是越高越好。</div>
      <div class="guide-line"><span class="guide-key">5MA／10MA／20MA</span>：短中期平均成本。股價與均線一起向上，比只站上一條均線更健康。</div>
      <div class="guide-line"><span class="guide-key">20 日突破</span>：是否突破近 20 個交易日的重要高點。</div>
      <div class="guide-line"><span class="guide-key">均線多頭</span>：短期均線是否大致排列在長期均線上方，代表趨勢結構較完整。</div>
      <div class="guide-line"><span class="guide-key">流動性</span>：看平均成交金額夠不夠。太低的股票即使分數漂亮，也可能不好進出。</div>
    </div>

    <div class="guide-title">⑫ 支撐、壓力與階段標籤</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">支撐</span>：價格回落時，較可能出現承接的區域。</div>
      <div class="guide-line"><span class="guide-key">壓力</span>：價格往上時，較容易遇到賣壓的區域。</div>
      <div class="guide-line">系統不是只抓一條均線，而是綜合前高前低、均線、成交密集區、突破平台、缺口等證據，整理成「區域」。所以請把它當決策區，不是保證反彈的精準價格。</div>
      <div class="guide-line"><span class="guide-key">🔥 剛啟動</span>：條件剛開始轉強，重點看突破能不能守住。</div>
      <div class="guide-line"><span class="guide-key">🟡 等回踩</span>：趨勢可能仍好，但位置不適合直接追，等回測比較安全。</div>
      <div class="guide-line"><span class="guide-key">🔵 觀察</span>：條件還沒完整，先放清單。</div>
      <div class="guide-line"><span class="guide-key">🚫 過熱不追</span>：短線延伸太大或追價風險偏高，不代表公司不好，只代表現在的位置不漂亮。</div>
    </div>

    <div class="guide-title">⑬ 第一次使用，照這個順序最快</div>
    <div class="guide-card">
      <div class="guide-line"><b>盤中：</b>① 看大盤 15 分 → ② 看族群成交資金輪動 → ③ 找同族群高動能個股 → ④ 看 VWAP、量速、相對強弱與階段 → ⑤ 最後才決定要不要追、等回踩或只觀察。</div>
      <div class="guide-line"><b>盤後：</b>① 看大盤環境 → ② 看法人族群資金流 → ③ 看個股波段延續 → ④ 再看進場位置 → ⑤ 用籌碼、支撐壓力確認隔日計畫。</div>
      <div class="guide-tip"><b>最後一句：</b>分數是「條件有沒有一起出現」，不是上漲機率。最有用的不是找 100 分，而是找「市場配合、族群配合、個股配合，而且位置也合理」的股票。</div>
    </div>
   </div>
 </details>'''

pattern = re.compile(r'<details class="help">\s*<summary>❓ 每個數值怎麼看？[^<]*</summary>\s*<div class="helptext">.*?</div>\s*</details>', re.S)
if not pattern.search(s):
    raise SystemExit("help block not found")
s = pattern.sub(new_help, s, count=1)

s = s.replace('Free Edition v1.5.15｜Safari強制換版修復＋盤後今日法人金額排名＋盤中成交資金輪動透明化',
              'Free Edition v1.5.16｜新手教學重寫＋盤後今日法人金額排名＋盤中成交資金輪動透明化', 1)
s = s.replace('./sw.js?v=1515', './sw.js?v=1516', 1)
s = s.replace('dogsonSwReloaded1515', 'dogsonSwReloaded1516')

INDEX.write_text(s, encoding="utf-8")

sw = SW.read_text(encoding="utf-8")
sw = re.sub(r"dogson-free-v\d+", "dogson-free-v1516", sw, count=1)
SW.write_text(sw, encoding="utf-8")

print("v1.5.16 beginner help rewrite applied")

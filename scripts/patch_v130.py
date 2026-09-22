from pathlib import Path
import re

p = Path('docs/index.html')
h = p.read_text(encoding='utf-8')

h = h.replace('Free Edition v1.2.3｜上櫃CSV備援＋流動性修正版', 'Free Edition v1.3｜近即時報價＋5分K結構')
h = h.replace('Free Edition v1.2.2｜上櫃＋流動性修正版', 'Free Edition v1.3｜近即時報價＋5分K結構')
h = h.replace('Free Edition v1.2.1｜盤中搜尋修正版', 'Free Edition v1.3｜近即時報價＋5分K結構')

anchor = '<div class="meta"><span id="modeText">盤中：5分K / VWAP / 量速</span><span id="updated">—</span></div>'
if 'id="liveStatus"' not in h:
    h = h.replace(anchor, '<div id="liveStatus" class="live-status warn">🟡 近即時報價準備中｜技術結構仍採5分K</div>\n' + anchor, 1)

h = h.replace(
    '<div class="note">盤中籌碼使用最近已完成交易日的外資／投信／融資／借券資料，不會把尚未公布的今日籌碼冒充成即時資料。免費資料源與 GitHub Actions 排程都可能延遲數分鐘。</div>',
    '<div class="note">盤中分成兩層：卡片上方「近即時價／近即時漲跌」由瀏覽器約每10秒嘗試更新、最多追蹤5檔；VWAP、量速、突破、支撐壓力與階段判斷仍採5分K雷達。籌碼使用最近已完成交易日資料，不會把尚未公布的今日籌碼冒充成即時資料。</div>'
)

h = h.replace(
    '<b>VWAP：</b>今天市場的成交量加權平均成本；站上通常偏強，但離太遠反而容易追高。<br>',
    '<b>近即時價：</b>搜尋標的、我的關注與目前畫面股票會依優先順序放進最多5檔即時池，每10秒嘗試刷新；不是券商逐筆成交串流。<br><b>5分K結構：</b>VWAP、量速、突破、支撐壓力與階段仍以5分K計算，避免逐筆雜訊讓訊號一直跳。<br><b>VWAP：</b>今天市場的成交量加權平均成本；站上通常偏強，但離太遠反而容易追高。<br>'
)

dup = '<b>流動性：</b>20日平均成交金額低於3,000萬直接排除；3,000萬～8,000萬標示偏低並降低品質分；8,000萬～2億正常；2億以上活躍。<br><b>流動性：</b>20日平均成交金額低於3,000萬直接排除；3,000萬～8,000萬標示偏低並降低品質分；8,000萬～2億正常；2億以上活躍。<br>'
h = h.replace(dup, '<b>流動性：</b>20日平均成交金額低於3,000萬直接排除；3,000萬～8,000萬標示偏低並降低品質分；8,000萬～2億正常；2億以上活躍。<br>')
h = h.replace(' ± 流動性修正 ± 流動性修正', ' ± 流動性修正')

scripts = '<script src="./realtime-config.js?v=130"></script>\n<script src="./realtime.js?v=130"></script>'
if '<script src="./realtime-config.js?v=130"></script>' not in h:
    if '<script src="./realtime.js?v=130"></script>' in h:
        h = h.replace('<script src="./realtime.js?v=130"></script>', scripts, 1)
    else:
        h = h.replace('</body>', scripts + '\n</body>', 1)

p.write_text(h, encoding='utf-8')

sw = Path('docs/sw.js')
if sw.exists():
    s = sw.read_text(encoding='utf-8')
    s = re.sub(r"const CACHE='[^']+'", "const CACHE='dogson-free-v130'", s, count=1)
    if "./realtime.js?v=130" not in s:
        s = s.replace("cache.addAll(['./manifest.webmanifest'])", "cache.addAll(['./manifest.webmanifest','./realtime-config.js?v=130','./realtime.js?v=130'])")
    elif "./realtime-config.js?v=130" not in s:
        s = s.replace("'./realtime.js?v=130'", "'./realtime-config.js?v=130','./realtime.js?v=130'")
    sw.write_text(s, encoding='utf-8')

b = Path('scripts/build_data.py')
if b.exists():
    x = b.read_text(encoding='utf-8')
    x = x.replace('Free Edition v1.2.3', 'Free Edition v1.3')
    x = x.replace('"version": "1.2.3-free"', '"version": "1.3-free"')
    b.write_text(x, encoding='utf-8')

print('v1.3 UI patch applied')

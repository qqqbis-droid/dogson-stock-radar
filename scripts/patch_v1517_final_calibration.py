#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final calibration for v1.5.17 Stage Engine 2.0.

Tighten only the close-mode '轉弱警戒' bucket after the full-market dry run.
Scoring, setup, launch, pullback, trend-hold, failure and overheat logic stay unchanged.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "scripts" / "build_data.py"
s = p.read_text(encoding="utf-8")

old = '''    core_weak = bool(
        below20
        or (ma5 > 0 and ma10 > 0 and ma5 < ma10)
        or swing < 52
        or (macd_h < 0 and macd_acc < 0)
    )
    if core_weak and len(weak_hits) >= 4:
        r["category"] = "轉弱警戒"
        r["stage_reason"] = "價格／均線已有弱化，且動能、籌碼或族群等多項訊號同步轉差；尚未確認結構失效"
        r["stage_risks"] = weak_hits[:4]
        return
'''
new = '''    # Final calibration：庫存管理的「轉弱警戒」必須比一般回檔更嚴格。
    # 核心價格/均線真的弱化 + 至少五項證據才亮警報，避免盤整股滿屏警告。
    ma_short_broken = bool(ma5 > 0 and ma10 > 0 and ma5 < ma10)
    core_weak = bool(
        (below20 and ma_short_broken)
        or swing < 48
        or (macd_h < 0 and macd_acc < 0 and ret5 <= -2)
    )
    if core_weak and len(weak_hits) >= 5:
        r["category"] = "轉弱警戒"
        r["stage_reason"] = "價格／短均已有明確弱化，且至少五項技術、動能、籌碼或族群訊號同步轉差；尚未確認結構失效"
        r["stage_risks"] = weak_hits[:5]
        return
'''
if old not in s:
    raise SystemExit('final calibration marker not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# Force Safari/PWA to see the final calibrated data/code release.
idx = ROOT / 'docs' / 'index.html'
h = idx.read_text(encoding='utf-8')
h = h.replace('./sw.js?v=1517', './sw.js?v=1517b')
h = h.replace('dogsonSwReloaded1517', 'dogsonSwReloaded1517b')
idx.write_text(h, encoding='utf-8')

sw = ROOT / 'docs' / 'sw.js'
w = sw.read_text(encoding='utf-8')
w = re.sub(r'dogson-free-v1517\b', 'dogson-free-v1517b', w, count=1)
sw.write_text(w, encoding='utf-8')

print('v1.5.17 final warning calibration applied')

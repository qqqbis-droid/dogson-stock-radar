#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Calibration pass for v1.5.17 Stage Engine 2.0.

The first full-market dry run was intentionally conservative and exposed two issues:
- too many stocks were labelled structural failure / weakness;
- healthy established trends were under-classified.

This pass keeps all 100-point scoring untouched and only calibrates stage thresholds.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "scripts" / "build_data.py"
s = P.read_text(encoding="utf-8")


def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"v1.5.17 calibration missing marker: {label}")
    s = s.replace(old, new, 1)


# 盤後「結構失效」必須是明顯跌破20MA + 中期結構同步壞掉；
# 不能只因為一般弱勢/盤整就判失效。
rep(
'''    if below20 and len(invalid_hits) >= 3 and (close < ma20 * 0.97 or tech < 18):
        r["category"] = "結構失效"
        r["stage_reason"] = "20MA與中短期趨勢多項同步失守，原波段結構需重新評估"
        r["stage_risks"] = invalid_hits[:4]
        return
''',
'''    hard_break20 = bool(ma20 > 0 and close < ma20 * 0.96)
    midtrend_broken = bool(ma10 > 0 and ma20 > 0 and ma10 < ma20)
    deep_momentum_loss = bool(ret5 <= -8 or (macd_h < 0 and tech < 14))
    if hard_break20 and midtrend_broken and deep_momentum_loss and len(invalid_hits) >= 4:
        r["category"] = "結構失效"
        r["stage_reason"] = "明顯跌破20MA，且中期均線與動能同步失守；原波段結構需重新評估"
        r["stage_risks"] = invalid_hits[:4]
        return
''',
"close structural failure"
)

# 趨勢持有是「持有狀態」，不該被總分70單點卡死；
# 只要價格/均線保持健康，搭配足夠的技術或延續品質即可成立。
rep(
'''    trend_hold = bool(
        trend and swing >= 70 and 0 <= dist20 <= 15 and ret5 <= 22
    )
''',
'''    trend_structure = bool(
        ma20 > 0 and close >= ma20
        and ma5 > 0 and ma10 > 0
        and ma5 >= ma10
        and ma10 >= ma20 * 0.995
    )
    trend_hold = bool(
        (trend or trend_structure)
        and (swing >= 60 or tech >= 30)
        and 1.5 <= dist20 <= 15
        and -2 <= ret5 <= 22
    )
''',
"close trend hold"
)

# 一般「轉弱警戒」也改成真正多證據：至少4項，且至少要有一項核心技術/價格弱化。
rep(
'''    if len(weak_hits) >= 3:
        r["category"] = "轉弱警戒"
        r["stage_reason"] = "技術、動能、籌碼或族群已有多項轉弱，但尚未確認結構失效"
        r["stage_risks"] = weak_hits[:4]
        return
''',
'''    core_weak = bool(
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
''',
"close weak warning"
)

# 盤中同樣避免普通震盪被直接判失效：需要更深的VWAP跌破 + 四項弱化 + 更低動能。
rep(
'''        if vwap > 0 and close < vwap * 0.985 and len(invalid_hits) >= 3 and score < 55:
            r["category"] = "結構失效"
            r["stage_reason"] = "VWAP、短線動能與相對強弱多項同步失守"
            r["stage_risks"] = invalid_hits[:4]
            return
''',
'''        if vwap > 0 and close < vwap * 0.975 and len(invalid_hits) >= 4 and score < 45 and rel <= -0.5:
            r["category"] = "結構失效"
            r["stage_reason"] = "價格明顯跌離VWAP，且短線動能、趨勢與相對強弱多項同步失守"
            r["stage_risks"] = invalid_hits[:4]
            return
''',
"intraday structural failure"
)

# 盤中轉弱至少四項，避免一個正常回踩就變成警報。
rep(
'''        if len(weak_hits) >= 3:
            r["category"] = "轉弱警戒"
            r["stage_reason"] = "多項盤中條件正在惡化，但尚未達結構失效"
            r["stage_risks"] = weak_hits[:4]
            return
''',
'''        core_weak = bool(
            (vwap > 0 and close < vwap)
            or ret15 <= -0.8
            or rel <= -0.8
            or score < 50
        )
        if core_weak and len(weak_hits) >= 4:
            r["category"] = "轉弱警戒"
            r["stage_reason"] = "價格／相對強弱已有弱化，且量能、短線趨勢或族群等訊號同步轉差"
            r["stage_risks"] = weak_hits[:4]
            return
''',
"intraday weak warning"
)

P.write_text(s, encoding="utf-8")
print("v1.5.17 Stage Engine 2.0 calibration applied")

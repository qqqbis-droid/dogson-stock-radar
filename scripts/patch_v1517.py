#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.17 — Stage Engine 2.0.

目標：不改盤中/盤後100分公式，只把股票生命週期從四類升級成：
蓄勢待發 / 剛啟動 / 回踩承接 / 趨勢持有 / 觀察 / 轉弱警戒 / 結構失效 / 過熱不追。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must_replace(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.17 patch missing marker: {label}")
    return text.replace(old, new, count)


STAGE_HELPER = r'''
def _assign_stage_v2(r, preliminary_intraday, sector_score_10):
    """Stage Engine 2.0：只判斷生命週期，不改任何100分權重。

    原則：
    1) 發動與蓄勢要有多項證據，不因單一指標亮燈。
    2) 轉弱與失效分開；失效採保守多證據確認，避免一根雜訊K誤殺。
    3) 盤中看 VWAP / 5分結構 / 相對市場 / 族群；盤後看均線 / MACD / 量價 / 籌碼 / 族群。
    """
    def f(key, default=0.0):
        try:
            v = r.get(key)
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)

    r["stage_version"] = "2.0"
    r["stage_signals"] = []
    r["stage_risks"] = []

    over = list(r.get("overheat_reasons") or [])
    if over:
        r["category"] = "過熱不追"
        r["stage_reason"] = "趨勢可能仍強，但短線延伸或波動已不適合追價"
        r["stage_risks"] = over[:4]
        return

    sec = float(sector_score_10 or 0)

    if preliminary_intraday:
        close = f("close")
        vwap = f("vwap")
        pace = f("pace")
        ret15 = f("ret15")
        tech = f("technical_score")
        score = f("intraday_score", f("score"))
        rel = float(((r.get("intraday_components") or {}).get("relative_strength_pct")) or 0)
        trend5 = bool(r.get("trend5"))
        break3 = bool(r.get("break3"))
        break12 = bool(r.get("break12"))
        above_vwap = bool(vwap > 0 and close >= vwap)
        near_vwap = bool(vwap > 0 and close >= vwap * 0.995 and close <= vwap * 1.02)

        invalid_flags = [
            (vwap > 0 and close < vwap * 0.985, "明顯跌破VWAP"),
            (ret15 <= -1.0, "近15分鐘明顯走弱"),
            (not trend5, "5分短均未維持多頭"),
            (rel <= -1.0, "明顯弱於所屬市場"),
            (score < 50, "盤中動能低於50"),
        ]
        invalid_hits = [txt for ok, txt in invalid_flags if ok]
        if vwap > 0 and close < vwap * 0.985 and len(invalid_hits) >= 3 and score < 55:
            r["category"] = "結構失效"
            r["stage_reason"] = "VWAP、短線動能與相對強弱多項同步失守"
            r["stage_risks"] = invalid_hits[:4]
            return

        launch = bool(
            break3 and above_vwap and pace >= 1.1 and rel >= 0
            and (trend5 or break12 or tech >= 22)
        )
        if launch:
            r["category"] = "剛啟動"
            r["stage_reason"] = "突破＋站上VWAP＋量速與相對強度同步轉強"
            r["stage_signals"] = ["3K突破", "站上VWAP", f"量速{pace:.1f}x", f"相對市場{rel:+.1f}%"]
            return

        pullback = bool(
            (break12 or score >= 70)
            and near_vwap
            and -1.0 <= ret15 <= 1.2
            and rel >= -0.3
            and (trend5 or tech >= 25)
        )
        if pullback:
            r["category"] = "回踩承接"
            r["stage_reason"] = "原結構仍強，價格回到VWAP附近測試承接"
            r["stage_signals"] = ["靠近VWAP", "短線結構未破", "相對市場未明顯轉弱"]
            return

        trend_hold = bool(
            score >= 70 and above_vwap and rel >= 0
            and (trend5 or break12)
        )
        if trend_hold:
            r["category"] = "趨勢持有"
            r["stage_reason"] = "動能、VWAP與相對市場仍支持既有上升趨勢"
            r["stage_signals"] = ["站上VWAP", f"盤中動能{score:.0f}", f"相對市場{rel:+.1f}%"]
            return

        setup_flags = [
            (near_vwap, "價格貼近VWAP"),
            (0.8 <= pace <= 2.5, "量速溫和升溫"),
            (rel >= -0.2, "沒有明顯落後市場"),
            (sec >= 5.0, "族群有共振"),
            (trend5 or break12 or tech >= 20, "短線結構正在靠攏"),
            (-0.5 <= ret15 <= 1.5, "15分鐘未急拉急殺"),
        ]
        setup_hits = [txt for ok, txt in setup_flags if ok]
        if not break3 and score >= 55 and len(setup_hits) >= 4:
            r["category"] = "蓄勢待發"
            r["stage_reason"] = "尚未正式突破，但價格、量能、相對強弱與族群條件正在集中"
            r["stage_signals"] = setup_hits[:4]
            return

        weak_flags = [
            (vwap > 0 and close < vwap, "跌回VWAP下方"),
            (ret15 < -0.3, "近15分鐘轉弱"),
            (rel < -0.3, "開始落後所屬市場"),
            (pace < 0.8, "量能降溫"),
            (sec < 4.0, "族群共振偏弱"),
            (not trend5, "5分短均未維持多頭"),
        ]
        weak_hits = [txt for ok, txt in weak_flags if ok]
        if len(weak_hits) >= 3:
            r["category"] = "轉弱警戒"
            r["stage_reason"] = "多項盤中條件正在惡化，但尚未達結構失效"
            r["stage_risks"] = weak_hits[:4]
            return

        r["category"] = "觀察"
        r["stage_reason"] = "目前沒有形成明確蓄勢、發動或轉弱共識"
        return

    # ---- 盤後波段 Stage 2.0 ----
    close = f("close")
    ma5 = f("ma5")
    ma10 = f("ma10")
    ma20 = f("ma20")
    dist20 = f("dist20", 999)
    ret5 = f("ret5", 999)
    day = f("day_change")
    vol = f("vol_x")
    rsi_v = f("rsi")
    macd_h = f("macd_h")
    macd_acc = f("macd_acc")
    tech = f("technical_score")
    swing = f("swing_quality_score", f("score"))
    chip = f("chip_score", 12.5)
    chip_cov = f("chip_coverage_pct")
    trend = bool(r.get("trend"))
    break3 = bool(r.get("break3"))
    break20 = bool(r.get("break20"))

    below20 = bool(ma20 > 0 and close < ma20)
    invalid_flags = [
        (ma20 > 0 and close < ma20 * 0.97, "收盤明顯跌破20MA"),
        (ma5 > 0 and ma10 > 0 and ma5 < ma10, "5MA跌破10MA"),
        (ma10 > 0 and ma20 > 0 and ma10 < ma20, "10MA跌破20MA"),
        (macd_h < 0, "MACD柱體在零軸下"),
        (ret5 <= -5, "近5日明顯回落"),
        (tech < 18, "日K技術分偏低"),
    ]
    invalid_hits = [txt for ok, txt in invalid_flags if ok]
    if below20 and len(invalid_hits) >= 3 and (close < ma20 * 0.97 or tech < 18):
        r["category"] = "結構失效"
        r["stage_reason"] = "20MA與中短期趨勢多項同步失守，原波段結構需重新評估"
        r["stage_risks"] = invalid_hits[:4]
        return

    launch_structure = bool(break20 or (break3 and trend))
    launch = bool(
        launch_structure and vol >= 1.2 and dist20 <= 12 and ret5 <= 18
        and close >= ma20 and (tech >= 28 or swing >= 65)
    )
    if launch:
        r["category"] = "剛啟動"
        r["stage_reason"] = "突破結構成立，量能與波段品質同步支持發動"
        r["stage_signals"] = ["20日突破" if break20 else "3日平台突破", f"量比{vol:.1f}x", f"距20MA {dist20:+.1f}%"]
        return

    pullback = bool(
        close >= ma20 * 0.995
        and -0.5 <= dist20 <= 8
        and ret5 <= 12
        and day <= 1.5
        and vol <= 1.8
        and (trend or swing >= 72 or tech >= 30)
    )
    if pullback:
        r["category"] = "回踩承接"
        r["stage_reason"] = "既有趨勢尚未破壞，價格回到20MA／支撐附近等待承接"
        r["stage_signals"] = ["守在20MA附近", "短線未過度延伸", "量能未失控"]
        return

    trend_hold = bool(
        trend and swing >= 70 and 0 <= dist20 <= 15 and ret5 <= 22
    )
    if trend_hold:
        r["category"] = "趨勢持有"
        r["stage_reason"] = "均線與波段延續分仍支持上升趨勢，重點是守住主要支撐"
        r["stage_signals"] = ["均線多頭", f"波段延續{swing:.0f}", f"距20MA {dist20:+.1f}%"]
        return

    # 蓄勢分不是新的交易總分，只用來確認「突破前條件集中度」。
    setup_points = 0
    setup_hits = []
    def add_setup(ok, pts, label):
        nonlocal setup_points
        if ok:
            setup_points += pts
            setup_hits.append(label)

    add_setup(ma20 > 0 and close >= ma20 * 0.99, 20, "守在20MA附近或上方")
    add_setup(ma5 > 0 and ma10 > 0 and ma5 >= ma10 * 0.995, 15, "5MA與10MA靠攏偏多")
    add_setup(macd_acc > 0 or macd_h > 0, 15, "MACD動能改善")
    add_setup(48 <= rsi_v <= 68, 10, "RSI位於健康蓄力區")
    add_setup(0.6 <= vol <= 1.8, 10, "量能沒有失控")
    add_setup(-1.5 <= dist20 <= 8, 10, "位置未過度延伸")
    add_setup(-3 <= ret5 <= 10, 10, "近5日仍在可蓄勢區")
    add_setup(chip_cov < 60 or chip >= 12.5, 5, "籌碼未明顯拖累")
    add_setup(sec >= 5.0, 5, "族群已有共振")

    if not trend and not break20 and setup_points >= 65 and tech >= 20:
        r["category"] = "蓄勢待發"
        r["stage_reason"] = "尚未完成正式突破，但均線、動能、位置、量能與籌碼／族群條件正在集中"
        r["stage_signals"] = setup_hits[:5]
        r["setup_evidence_score"] = setup_points
        return

    weak_flags = [
        (below20, "收盤跌到20MA下方"),
        (ma5 > 0 and ma10 > 0 and ma5 < ma10, "5MA低於10MA"),
        (macd_acc < 0, "MACD動能下降"),
        (ret5 < 0, "近5日報酬轉負"),
        (chip_cov >= 60 and chip < 10, "籌碼分偏弱"),
        (sec < 4.0, "族群共振偏弱"),
        (swing < 60, "波段延續分下降"),
    ]
    weak_hits = [txt for ok, txt in weak_flags if ok]
    if len(weak_hits) >= 3:
        r["category"] = "轉弱警戒"
        r["stage_reason"] = "技術、動能、籌碼或族群已有多項轉弱，但尚未確認結構失效"
        r["stage_risks"] = weak_hits[:4]
        return

    r["category"] = "觀察"
    r["stage_reason"] = "目前條件尚未集中成蓄勢／發動，也沒有足夠證據判定轉弱"
'''


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    if "def _assign_stage_v2(" not in s:
        marker = "def add_component_scores(rows, market, preliminary_intraday=False):"
        if marker not in s:
            raise SystemExit("v1.5.17 cannot find add_component_scores")
        s = s.replace(marker, STAGE_HELPER + "\n\n" + marker, 1)

    start = s.find('        if r.get("overheat_reasons"):', s.find('def add_component_scores'))
    end_marker = '    quality_order = {"強動能": 0, "高延續": 0, "轉強": 1, "強": 1, "中性": 2, "一般": 2, "轉弱": 3, "資料待補": 4}'
    end = s.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit("v1.5.17 cannot locate old stage block")
    replacement = '''        _assign_stage_v2(r, preliminary_intraday, sec)\n\n    order = {\n        "剛啟動": 0, "蓄勢待發": 1, "回踩承接": 2, "趨勢持有": 3,\n        "觀察": 4, "轉弱警戒": 5, "結構失效": 6, "過熱不追": 7,\n    }\n'''
    s = s[:start] + replacement + s[end:]
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.12", "犬子老師飆股雷達 Free Edition v1.5.17", 1)
    s = s.replace('"version": "1.5.14-free"', '"version": "1.5.17-free"')
    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = re.sub(
        r"Free Edition v1\.5\.16｜[^<]*",
        "Free Edition v1.5.17｜Stage Engine 2.0＋新手教學＋法人金額力度",
        s,
        count=1,
    )

    old_css = '.cat{display:inline-block;font-size:12px;font-weight:850;padding:6px 9px;border-radius:999px;margin-top:7px}.start{background:#0f3928;color:#69efa8}.pull{background:#40300f;color:#ffd477}.watch{background:#1b2b42;color:#9cc9ff}.hot{background:#441923;color:#ff9aab}'
    new_css = '.cat{display:inline-block;font-size:12px;font-weight:850;padding:6px 9px;border-radius:999px;margin-top:7px}.setup{background:#173527;color:#9ef0bd}.start{background:#0f3928;color:#69efa8}.pull{background:#40300f;color:#ffd477}.trendhold{background:#17304a;color:#b9ddff}.watch{background:#1b2b42;color:#9cc9ff}.weak{background:#4a3213;color:#ffd08a}.invalid{background:#471820;color:#ff9cac}.hot{background:#3c1d3f;color:#eab4ff}'
    s = must_replace(s, old_css, new_css, "stage badge css")

    old_filters = '<button class="filter on" data-f="all">全部</button><button class="filter" data-f="剛啟動">🔥 剛啟動</button><button class="filter" data-f="等回踩">🟡 等回踩</button><button class="filter" data-f="過熱不追">🚫 過熱</button><button class="filter" id="watchOnly">⭐ 我的關注</button>'
    new_filters = '<button class="filter on" data-f="all">全部</button><button class="filter" data-f="蓄勢待發">🌱 蓄勢</button><button class="filter" data-f="剛啟動">🔥 剛啟動</button><button class="filter" data-f="回踩承接">🟡 回踩</button><button class="filter" data-f="趨勢持有">🚂 趨勢</button><button class="filter" data-f="轉弱警戒">⚠️ 轉弱</button><button class="filter" data-f="結構失效">❌ 失效</button><button class="filter" data-f="過熱不追">🚫 過熱</button><button class="filter" id="watchOnly">⭐ 我的關注</button>'
    s = must_replace(s, old_filters, new_filters, "stage filters")

    old_cls = 'function cls(c){return c==="剛啟動"?"start":c==="等回踩"?"pull":c==="過熱不追"?"hot":"watch"}'
    new_cls = 'function cls(c){return c==="蓄勢待發"?"setup":c==="剛啟動"?"start":c==="回踩承接"?"pull":c==="趨勢持有"?"trendhold":c==="轉弱警戒"?"weak":c==="結構失效"?"invalid":c==="過熱不追"?"hot":"watch"}'
    s = must_replace(s, old_cls, new_cls, "stage css classifier")

    old_help = '''      <div class="guide-line"><span class="guide-key">🔥 剛啟動</span>：條件剛開始轉強，重點看突破能不能守住。</div>\n      <div class="guide-line"><span class="guide-key">🟡 等回踩</span>：趨勢可能仍好，但位置不適合直接追，等回測比較安全。</div>\n      <div class="guide-line"><span class="guide-key">🔵 觀察</span>：條件還沒完整，先放清單。</div>\n      <div class="guide-line"><span class="guide-key">🚫 過熱不追</span>：短線延伸太大或追價風險偏高，不代表公司不好，只代表現在的位置不漂亮。</div>'''
    new_help = '''      <div class="guide-line"><span class="guide-key">🌱 蓄勢待發</span>：還沒正式突破，但均線、動能、量能、相對強弱、籌碼或族群已開始集中，適合放進「蹲車名單」。</div>\n      <div class="guide-line"><span class="guide-key">🔥 剛啟動</span>：突破已出現，而且量能／VWAP／趨勢有同步確認，開始找第一筆進場機會。</div>\n      <div class="guide-line"><span class="guide-key">🟡 回踩承接</span>：已經有過一段強勢，現在回到VWAP、20MA或支撐附近，結構尚未破壞。</div>\n      <div class="guide-line"><span class="guide-key">🚂 趨勢持有</span>：不是新的追價訊號，而是既有上升趨勢仍健康；持有者重點看主要支撐有沒有守住。</div>\n      <div class="guide-line"><span class="guide-key">🔵 觀察</span>：多空證據還不夠集中，暫時沒有必要急著動作。</div>\n      <div class="guide-line"><span class="guide-key">⚠️ 轉弱警戒</span>：已有多項條件惡化，但還沒有確認結構失效；持有者應停止追價並提高警覺。</div>\n      <div class="guide-line"><span class="guide-key">❌ 結構失效</span>：VWAP／20MA、短均、動能等多項條件同步失守。系統採多證據確認，不會因單一黑K就判定失效。</div>\n      <div class="guide-line"><span class="guide-key">🚫 過熱不追</span>：股票可能仍強，但短線延伸或波動過大；意思是「現在不適合追」，不是看空。</div>'''
    s = must_replace(s, old_help, new_help, "stage help")

    s = s.replace('./sw.js?v=1516', './sw.js?v=1517')
    s = s.replace('dogsonSwReloaded1516', 'dogsonSwReloaded1517')
    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1517", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_build_data()
    patch_index()
    patch_sw()
    print("v1.5.17 Stage Engine 2.0 patch applied")

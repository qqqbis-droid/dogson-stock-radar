#!/usr/bin/env python3
from pathlib import Path


def patch_bridge(path_name: str):
    p = Path(path_name)
    s = p.read_text(encoding='utf-8')

    # Preserve the actual calendar date of the structural bar.  A bare HH:MM
    # must never be reinterpreted as today's structure on a later session.
    old = '        row["structure_time"] = t.get("time")\n        row["structure_close"] = t.get("close")'
    new = '        row["structure_time"] = t.get("time")\n        row["structure_date"] = str(t.get("date") or "")[:10] or None\n        row["structure_close"] = t.get("close")'
    if old in s and 'row["structure_date"]' not in s:
        s = s.replace(old, new, 1)

    marker = 'def _apply_live_truth_guard(rows, trade_date):'
    if marker not in s:
        insert_at = s.index('\ndef main():')
        helper = r'''

def _fnum(v):
    try:
        if v in (None, "", "-", "--"):
            return None
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def _apply_live_truth_guard(rows, trade_date):
    """Fail closed when the current order book disproves the structural price.

    The order book is NOT promoted to a fake last trade.  It is only used as an
    independent consistency witness.  A live score requires a same-session
    structure and a price that is not materially detached from the current book.
    """
    guarded = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        qd = str(row.get("quote_date") or "")[:10]
        if qd != str(trade_date)[:10]:
            continue
        structure_date = str(row.get("structure_date") or row.get("date") or "")[:10]
        structure_same_day = bool(structure_date and structure_date == str(trade_date)[:10])
        px = _fnum(row.get("close"))
        bid = _fnum(row.get("quote_bid1"))
        ask = _fnum(row.get("quote_ask1"))
        book = (bid + ask) / 2.0 if bid and ask else (bid or ask)
        gap = abs(px / book - 1.0) * 100.0 if px and book else None
        has_trade = bool(row.get("quote_has_trade")) and _fnum(row.get("quote_close")) is not None
        # 2% is deliberately much wider than a normal spread.  This gate is for
        # detecting stale-session price bases, not microstructure noise.
        book_consistent = gap is None or gap <= 2.0
        valid = bool(structure_same_day and (has_trade or book_consistent))
        row["quote_price_validated"] = valid
        row["quote_structure_gap_pct"] = round(gap, 2) if gap is not None else None
        row["structure_date_verified"] = structure_same_day
        if valid:
            row.pop("live_truth_blocker", None)
            continue
        guarded += 1
        reasons = []
        if not structure_same_day:
            reasons.append(f"5分結構日期 {structure_date or '未知'} ≠ 報價日 {trade_date}")
        if gap is not None and gap > 2.0:
            reasons.append(f"結構價與五檔差距 {gap:.1f}%")
        if not has_trade:
            reasons.append("本輪未驗證到真實成交價")
        row["live_truth_blocker"] = "；".join(reasons) or "盤中價格/結構一致性未通過"
        # Do not let stale structure produce a directional score or lifecycle.
        row["intraday_score"] = None
        row["intraday_momentum_score"] = None
        row["intraday_components"] = None
        row["category"] = "觀察"
        risks = list(row.get("stage_risks") or [])
        msg = "即時價格與5分結構尚未同時驗證，暫停盤中方向判定"
        if msg not in risks:
            risks.insert(0, msg)
        row["stage_risks"] = risks[:5]
        row["stage_signals"] = []
    print("LIVE_TRUTH_GUARD", guarded, "/", len(rows))
    return rows
'''
        s = s[:insert_at] + helper + s[insert_at:]

    # Apply after score calculation so a stale legacy score cannot survive.
    target = '    out_rows = bd.add_component_scores(out_rows, intraday_market, preliminary_intraday=True)\n'
    repl = target + '    out_rows = _apply_live_truth_guard(out_rows, trade_date)\n'
    if target in s and 'out_rows = _apply_live_truth_guard(out_rows, trade_date)' not in s:
        s = s.replace(target, repl, 1)

    p.write_text(s, encoding='utf-8')
    print('patched', path_name)


for name in ('scripts/bridge_intraday.py', 'scripts/bridge_intraday_fast.py'):
    patch_bridge(name)

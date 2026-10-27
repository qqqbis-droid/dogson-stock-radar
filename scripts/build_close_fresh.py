#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the close radar from the latest *completed* Taiwan cash session.

The close mission is intentionally different from intraday/daytrade: while the
cash market is still open, Yahoo daily bars may already expose today's partial
bar. A close build must never treat that partial bar as a completed session.

This wrapper therefore enforces the same completed-session cutoff on both MIS
and every Yahoo daily frame before ``build_data.build_close()`` sees them. MIS
is still preferred when it is current; stale MIS may be ignored, but the daily
fallback is capped to the latest completed session as well.

It also stamps chip provenance after the chip fetch finishes. ``chip_date``
means the source trading date; ``chip_checked_at`` means when our system most
recently completed an actual source check. These are deliberately separate.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import pandas as pd

import build_data as bd
import sync_chip_provenance
import daily_history_capture


_ORIGINAL_MIS = bd.official_mis_snapshot
_ORIGINAL_DOWNLOAD_DAILY = bd.download_daily
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
TAIPEI_TZ = timezone(timedelta(hours=8))

# A broad official MIS close is the session anchor for all stock daily frames.
# Some Yahoo bars may be later than the latest exchange-completed session
# (especially over exchange holidays). Never mix those dates in one close.
_VERIFIED_MIS_CLOSE_DATE: date | None = None


def _frame_latest_date(frame) -> date | None:
    if frame is None or len(frame) == 0:
        return None
    try:
        idx = pd.to_datetime(frame.index, errors="coerce")
        idx = idx[~pd.isna(idx)]
        if len(idx) == 0:
            return None
        return max(x.date() for x in idx)
    except Exception:
        return None


def completed_daily(syms, period="6mo"):
    """Return Yahoo daily data with any not-yet-completed session removed."""
    data = _ORIGINAL_DOWNLOAD_DAILY(syms, period)
    cutoff = bd._latest_completed_cutoff()
    if _VERIFIED_MIS_CLOSE_DATE is not None:
        cutoff = min(cutoff, _VERIFIED_MIS_CLOSE_DATE)
    out = {}
    for sym, frame in (data or {}).items():
        try:
            if frame is None or frame.empty:
                continue
            idx = pd.to_datetime(frame.index, errors="coerce")
            keep = [not pd.isna(ts) and ts.date() <= cutoff for ts in idx]
            trimmed = frame.loc[keep].copy()
            if not trimmed.empty:
                out[sym] = trimmed
        except Exception as exc:
            print("completed daily filter", sym, exc)
    daily_history_capture.capture_frames(out)
    return out


def _latest_reference_date() -> date | None:
    """Latest verified exchange session, never a Yahoo-only daily-bar date.

    The official TPEx daily index history and TWSE MIS index are independent
    exchange clocks. Yahoo may emit a bar on an unscheduled market holiday
    (e.g. the 2026-10-23 typhoon closure), so its bar dates cannot establish
    a new cash trading session.
    """
    cutoff = bd._latest_completed_cutoff()
    evidence: list[date] = []
    try:
        d = _frame_latest_date(bd.tpex_index_history())
        if d and d <= cutoff:
            evidence.append(d)
    except Exception as exc:
        print("official TPEx trading-session reference failed:", exc)

    try:
        index = bd.official_index_snapshot()
        for item in index.values():
            raw = str(item.get("date") or "")[:10]
            if not raw:
                continue
            d = date.fromisoformat(raw)
            if d <= cutoff:
                evidence.append(d)
    except Exception as exc:
        print("official TWSE index trading-session reference failed:", exc)

    verified = max(evidence) if evidence else None
    print("official exchange-session reference:", verified, "evidence", evidence)
    return verified


def guarded_mis_snapshot(uni):
    global _VERIFIED_MIS_CLOSE_DATE
    _VERIFIED_MIS_CLOSE_DATE = None
    snap = _ORIGINAL_MIS(uni)
    cutoff = bd._latest_completed_cutoff()
    snap = {k: v for k, v in (snap or {}).items()
            if v.get("date") and v.get("date") <= cutoff}
    mis_latest = max((v["date"] for v in snap.values()), default=None)
    reference_latest = _latest_reference_date()

    if not reference_latest and not mis_latest:
        raise RuntimeError("No official exchange session evidence: refuse Yahoo-only close date")
    if mis_latest and reference_latest and reference_latest > mis_latest:
        print("freshness guard: stale MIS", mis_latest,
              "newer official index", reference_latest)
        snap = {}
        mis_latest = None

    required = max(200, int(len(uni) * 0.55))
    if mis_latest is not None and len(snap) >= required:
        _VERIFIED_MIS_CLOSE_DATE = mis_latest
        print("official full-market MIS session anchor:", mis_latest,
              "coverage", len(snap), "/", len(uni))
    elif reference_latest:
        _VERIFIED_MIS_CLOSE_DATE = reference_latest
        # An inconsistent or partial MIS response must not inject a different
        # day's prices into the official-index-anchored daily history.
        if mis_latest != reference_latest:
            snap = {}
        print("official index session anchor:", reference_latest,
              "MIS coverage", len(snap), "/", len(uni))
    else:
        # In the rare case the official indices are both unreachable but MIS
        # has broad, dated exchange coverage, the MIS full-market date is safe.
        raise RuntimeError("Official indices unavailable and MIS coverage insufficient")

    if snap and mis_latest != _VERIFIED_MIS_CLOSE_DATE:
        snap = {}
    return snap


def _chip_check_health(status: dict, rows: list[dict]) -> str:
    """Summarise source-check health without pretending stale data is current."""
    if not status or not status.get("updated_at"):
        return "UNCHECKED"

    diagnostics = [str(x).lower() for x in (status.get("diagnostics") or [])]
    errors = [
        x for x in diagnostics
        if " failed:" in x or " parser failed" in x or "response date mismatch" in x
    ]
    covered = sum(float(r.get("chip_coverage_pct") or 0) > 0 for r in rows)
    if rows and covered == 0:
        return "ERROR"
    if errors:
        return "PARTIAL"
    return "CHECKED"


def _max_source_date(rows: list[dict], key: str):
    vals = [str(r.get(key) or "")[:10] for r in rows]
    vals = [x for x in vals if len(x) == 10]
    return max(vals) if vals else None


def _normalize_chip_checked_at(raw):
    """Return a truthful +08:00 timestamp for the source-check wall clock.

    Historical chip_status used ``UTC now + 8h`` while retaining a ``+00:00``
    suffix.  That wall clock is already Taipei time, so converting it as UTC
    would add eight hours a second time in browsers. Reinterpret that legacy
    value with +08:00; properly offset timestamps are converted normally.
    """
    if not raw:
        return None
    text = str(raw).strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=TAIPEI_TZ).isoformat()
        if dt.utcoffset() == timedelta(0):
            # chip_data.py historically stored a Taipei wall clock with +00:00.
            return dt.replace(tzinfo=TAIPEI_TZ).isoformat()
        return dt.astimezone(TAIPEI_TZ).isoformat()
    except Exception:
        return text


def stamp_chip_provenance():
    """Attach actual source-check time to every close row and chip_status.

    chip_date/foreign_date/... remain the dates of the data itself. The check
    timestamp is never used as a substitute for those source dates.
    """
    close_path = DATA / "close.json"
    status_path = DATA / "chip_status.json"
    if not close_path.exists():
        return

    obj = json.loads(close_path.read_text(encoding="utf-8"))
    rows = [r for r in (obj.get("rows") or []) if isinstance(r, dict)]
    try:
        status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    except Exception:
        status = {}

    checked_at = _normalize_chip_checked_at(status.get("last_checked_at") or status.get("updated_at"))
    health = _chip_check_health(status, rows)
    source_dates = {
        "chip": _max_source_date(rows, "chip_date"),
        "foreign": _max_source_date(rows, "foreign_date"),
        "trust": _max_source_date(rows, "trust_date"),
        "sbl": _max_source_date(rows, "sbl_date"),
        "margin": _max_source_date(rows, "margin_date"),
    }

    for row in rows:
        row["chip_checked_at"] = checked_at
        row["chip_check_health"] = health
        row["chip_check_latest_attempt_date"] = str(checked_at or "")[:10] or None

    obj["rows"] = rows
    obj["chip_provenance"] = {
        "last_checked_at": checked_at,
        "check_health": health,
        "source_dates": source_dates,
        "semantics": {
            "source_date": "資料本身所屬交易日",
            "last_checked_at": "系統最後一次實際向籌碼來源完成查詢的時間",
        },
    }
    close_path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    if status_path.exists():
        status["last_checked_at"] = checked_at
        status["check_health"] = health
        status["latest_source_dates"] = source_dates
        status["date_semantics"] = {
            "source_date": "資料本身所屬交易日",
            "last_checked_at": "系統最後一次實際向籌碼來源完成查詢的時間",
        }
        status_path.write_text(json.dumps(status, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print("chip provenance:", "checked_at=", checked_at, "health=", health, "source_dates=", source_dates)


def main():
    # Patch the daily source first so every downstream fallback, including
    # index_state and the all-stock close build, is bound to completed sessions.
    bd.download_daily = completed_daily
    bd.official_mis_snapshot = guarded_mis_snapshot
    bd.build_close()
    stamp_chip_provenance()
    # Live missions are allowed to reuse the latest completed chip background,
    # but they inherit only the real source/check clocks, never a newer fake one.
    sync_chip_provenance.main()


if __name__ == "__main__":
    main()

# refresh-marker: 2026-10-04-persist-completed-daily-history

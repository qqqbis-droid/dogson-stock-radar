#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "contracts" / "registries" / "sector_registry.json"
UNIVERSE = ROOT / "docs" / "data" / "universe.json"
CLOSE = ROOT / "docs" / "data" / "close.json"

from scripts.sector_groups import (
    CODE_TO_RECORD,
    OFFICIAL_INDUSTRY_CORE_CODES,
    PRIMARY_GROUP_MIN_CONFIDENCE,
    PRIMARY_GROUP_MIN_PEERS,
    SECONDARY_GROUP_MIN_CONFIDENCE,
    TAXONOMY_VERSION,
    classification_for,
    industry_code_for,
    taxonomy_stats,
)

# These official industries are intentionally too heterogeneous to be promoted
# to full core-sector scoring solely from the exchange industry code.
BROAD_OFFICIAL_DENYLIST = {"24", "25", "26", "27", "28", "29", "31"}


def load(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"sector registry gate: invalid JSON {path}: {exc}")


def num(value, default=0.0):
    try:
        return float(value) if value is not None else float(default)
    except Exception:
        return float(default)


def resonance_score(group_rows):
    """Mirror build_data._resonance_stats score without importing heavy runtime deps."""
    total = len(group_rows)
    if not total:
        return 0.0
    strong = [
        x for x in group_rows
        if num(x.get("technical_score")) >= 30 and not x.get("overheat_reasons")
    ]
    up_pct = sum(1 for x in group_rows if num(x.get("day_change")) > 0) / total * 100
    strong_pct = len(strong) / total * 100
    avg_tech = sum(num(x.get("technical_score")) for x in group_rows) / total
    acts = []
    for x in group_rows:
        v = x.get("pace") if x.get("pace") is not None else x.get("vol_x")
        if v is not None:
            try:
                acts.append(float(v))
            except Exception:
                pass
    avg_activity = sum(acts) / len(acts) if acts else 1.0
    leaders = [
        x for x in group_rows
        if num(x.get("technical_score")) >= 35 and num(x.get("day_change")) >= 1
    ]
    trend_hits = sum(
        1 for x in group_rows
        if x.get("trend5") or x.get("trend") or x.get("break12") or x.get("break20")
    )
    continuity_pct = trend_hits / total * 100
    total_turn = sum(num(x.get("current_turnover")) for x in group_rows)
    strong_turn = sum(num(x.get("current_turnover")) for x in strong)
    strong_turn_pct = (strong_turn / total_turn * 100) if total_turn > 0 else strong_pct

    breadth = 3.0 if up_pct >= 70 else 2.5 if up_pct >= 60 else 1.5 if up_pct >= 50 else 0.5 if up_pct >= 40 else 0.0
    strength_basis = max(strong_pct, strong_turn_pct)
    strength = 2.0 if strength_basis >= 60 else 1.5 if strength_basis >= 45 else 1.0 if strength_basis >= 30 else 0.5 if avg_tech >= 25 else 0.0
    volume = 2.0 if avg_activity >= 2.0 else 1.5 if avg_activity >= 1.5 else 1.0 if avg_activity >= 1.2 else 0.5 if avg_activity >= 1.0 else 0.0
    leader = 2.0 if len(leaders) >= 2 else 1.2 if len(leaders) == 1 else 0.0
    continuity = 1.0 if continuity_pct >= 60 else 0.5 if continuity_pct >= 40 else 0.0
    return round(min(10.0, breadth + strength + volume + leader + continuity), 1)


def shadow_official_core_impact(close_rows):
    """Compare existing proxy score with proposed OFFICIAL_INDUSTRY_CORE score."""
    direct_rows = []
    groups = defaultdict(list)
    for row in close_rows:
        if not isinstance(row, dict):
            continue
        c = classification_for(row.get("code"), name=row.get("name"), industry=row.get("industry"))
        if c.get("score_source") == "OFFICIAL_INDUSTRY_CORE":
            direct_rows.append(row)
            groups[str(c.get("primary_group") or "")].append(row)

    new_sec_by_group = {g: resonance_score(rs) for g, rs in groups.items()}
    old_top_codes = [str(r.get("code") or "") for r in close_rows[:50]]
    records = []
    stage_sensitive = 0
    for old_rank, row in enumerate(close_rows, 1):
        c = classification_for(row.get("code"), name=row.get("name"), industry=row.get("industry"))
        if c.get("score_source") != "OFFICIAL_INDUSTRY_CORE":
            continue
        group = str(c.get("primary_group") or "")
        old_sec = num(row.get("sector_score"))
        new_sec = num(new_sec_by_group.get(group))
        weights = row.get("swing_weights") or {}
        sector_weight = num(weights.get("sector"), 15.0)
        score_delta = round((new_sec - old_sec) / 10.0 * sector_weight, 2)
        old_score = num(row.get("swing_quality_score"), num(row.get("score")))
        new_score = round(max(0.0, min(100.0, old_score + score_delta)), 1)
        thresholds = (48.0, 60.0, 65.0, 72.0)
        score_cross = any((old_score < t <= new_score) or (new_score < t <= old_score) for t in thresholds)
        sec_cross = (old_sec < 5 <= new_sec) or (new_sec < 5 <= old_sec) or (old_sec < 4 <= new_sec) or (new_sec < 4 <= old_sec)
        if score_cross or sec_cross:
            stage_sensitive += 1
        records.append({
            "code": str(row.get("code") or ""),
            "name": row.get("name"),
            "group": group,
            "old_rank": old_rank,
            "old_sector_score": round(old_sec, 1),
            "new_sector_score": round(new_sec, 1),
            "old_swing_score": round(old_score, 1),
            "new_swing_score": new_score,
            "score_delta": score_delta,
            "was_top50": str(row.get("code") or "") in old_top_codes,
            "stage_threshold_sensitive": bool(score_cross or sec_cross),
        })

    ranked = sorted(
        close_rows,
        key=lambda r: -(
            num(r.get("swing_quality_score"), num(r.get("score")))
            + next((x["score_delta"] for x in records if x["code"] == str(r.get("code") or "")), 0.0)
        ),
    )
    new_simple_rank = {str(r.get("code") or ""): i for i, r in enumerate(ranked, 1)}
    for rec in records:
        rec["new_score_only_rank"] = new_simple_rank.get(rec["code"])
        if rec["new_score_only_rank"] is not None:
            rec["score_only_rank_delta"] = int(rec["old_rank"] - rec["new_score_only_rank"])

    affected_top50 = [x for x in records if x["was_top50"]]
    max_abs_score_delta = max((abs(x["score_delta"]) for x in records), default=0.0)
    max_abs_rank_delta = max((abs(x.get("score_only_rank_delta") or 0) for x in records), default=0)
    biggest = sorted(records, key=lambda x: abs(x["score_delta"]), reverse=True)[:15]
    return {
        "affected_close_rows": len(records),
        "affected_top50": len(affected_top50),
        "stage_threshold_sensitive": stage_sensitive,
        "max_abs_swing_score_delta": round(max_abs_score_delta, 2),
        "max_abs_score_only_rank_delta": max_abs_rank_delta,
        "group_new_sector_scores": dict(sorted(new_sec_by_group.items())),
        "top50_changes": affected_top50,
        "largest_score_changes": biggest,
    }


def main():
    registry = load(REGISTRY, {})
    errors = []
    warnings = []
    seen = {}
    evidence_quality = Counter()

    if not isinstance(registry, dict):
        raise SystemExit("Sector Taxonomy registry must be an object")
    if str(registry.get("taxonomy_version") or "") != TAXONOMY_VERSION:
        errors.append(
            f"version mismatch registry={registry.get('taxonomy_version')} resolver={TAXONOMY_VERSION}"
        )

    leaked_broad = sorted(OFFICIAL_INDUSTRY_CORE_CODES & BROAD_OFFICIAL_DENYLIST)
    if leaked_broad:
        errors.append("broad official industries may not be core-only groups: " + ",".join(leaked_broad))

    for grow in registry.get("groups") or []:
        if not isinstance(grow, dict):
            errors.append("group row is not object")
            continue
        group = str(grow.get("group") or "").strip()
        try:
            conf = float(grow.get("confidence"))
        except Exception:
            errors.append(f"group {group or '?'} missing numeric confidence")
            conf = None
        refs = [str(x).strip() for x in (grow.get("evidence_urls_or_refs") or []) if str(x).strip()]
        quality = str(grow.get("evidence_quality") or "NONE")
        evidence_quality[quality] += 1
        if not group:
            errors.append("group missing name")
            continue
        if conf is not None and conf < PRIMARY_GROUP_MIN_CONFIDENCE:
            warnings.append(f"group {group}: confidence {conf} below core threshold")
        if not refs:
            errors.append(f"group {group}: no evidence reference")
        if quality == "NONE":
            errors.append(f"group {group}: evidence_quality=NONE")

        members = [str(x).strip() for x in (grow.get("members") or []) if str(x).strip()]
        if len(members) < PRIMARY_GROUP_MIN_PEERS:
            warnings.append(
                f"group {group}: only {len(members)} registry peers; cannot receive full core score"
            )
        for code in members:
            if code in seen:
                errors.append(f"duplicate primary code {code}: {seen[code]} vs {group}")
            seen[code] = group

    for code, override in (registry.get("stock_overrides") or {}).items():
        if not isinstance(override, dict):
            errors.append(f"{code}: override is not object")
            continue
        for sec in override.get("secondary_groups") or []:
            try:
                sconf = float(sec.get("confidence"))
            except Exception:
                errors.append(f"{code}: secondary group missing confidence")
                continue
            if sconf < SECONDARY_GROUP_MIN_CONFIDENCE:
                errors.append(f"{code}: secondary group below policy threshold {sconf}")

    if set(CODE_TO_RECORD) != (
        set(seen)
        | set(str(x) for x in (registry.get("stock_overrides") or {}))
        | set(str(x) for x in (registry.get("theme_tags") or {}))
    ):
        errors.append("resolver registry code set differs from source registry")

    universe = load(UNIVERSE, [])
    coverage = Counter()
    score_sources = Counter()
    evidence_status = Counter()
    official_counts = Counter()
    unclassified_codes = []
    if isinstance(universe, list):
        for row in universe:
            if not isinstance(row, dict):
                continue
            raw_industry = row.get("industry")
            ind_code = industry_code_for(raw_industry)
            if ind_code:
                official_counts[ind_code] += 1
            c = classification_for(row.get("code"), name=row.get("name"), industry=raw_industry)
            coverage[c["classification_status"]] += 1
            score_sources[c["score_source"]] += 1
            evidence_status[c["evidence_status"]] += 1
            if c["classification_status"] == "UNCLASSIFIED":
                unclassified_codes.append(str(row.get("code") or ""))
        if universe and unclassified_codes:
            errors.append(
                f"universe has {len(unclassified_codes)} truly UNCLASSIFIED stocks: "
                + ",".join(unclassified_codes[:20])
            )

    official_core_peer_counts = {
        code: int(official_counts.get(code, 0)) for code in sorted(OFFICIAL_INDUSTRY_CORE_CODES)
    }
    for code, count in official_core_peer_counts.items():
        if count < PRIMARY_GROUP_MIN_PEERS:
            errors.append(
                f"official-core industry {code} has only {count} universe peers; min={PRIMARY_GROUP_MIN_PEERS}"
            )

    close = load(CLOSE, {})
    close_rows = (close.get("rows") or []) if isinstance(close, dict) else []
    top = close_rows[:50]
    top_status = Counter()
    top_score_sources = Counter()
    top_evidence = Counter()
    top_unclassified = []
    for row in top:
        c = classification_for(row.get("code"), name=row.get("name"), industry=row.get("industry"))
        top_status[c["classification_status"]] += 1
        top_score_sources[c["score_source"]] += 1
        top_evidence[c["evidence_status"]] += 1
        if c["classification_status"] == "UNCLASSIFIED":
            top_unclassified.append(str(row.get("code") or ""))
    if top_unclassified:
        errors.append("top ranking pool contains UNCLASSIFIED: " + ",".join(top_unclassified))

    shadow_impact = shadow_official_core_impact(close_rows) if close_rows else {}
    if num(shadow_impact.get("max_abs_swing_score_delta")) > 9.1:
        errors.append("official-core score impact exceeds mathematical sector cap")
    if int(shadow_impact.get("affected_top50") or 0) > 15:
        errors.append("official-core policy unexpectedly touches more than 15 of current top50")

    stats = taxonomy_stats()
    report = {
        "status": "FAIL" if errors else "PASS",
        "taxonomy_version": TAXONOMY_VERSION,
        "registry_entries": stats.get("registry_entries"),
        "eligible_registry_primary_codes": stats.get("eligible_primary_codes"),
        "registry_primary_groups": stats.get("primary_groups"),
        "official_industry_core_codes": sorted(OFFICIAL_INDUSTRY_CORE_CODES),
        "official_core_peer_counts": official_core_peer_counts,
        "universe_rows": len(universe) if isinstance(universe, list) else 0,
        "universe_status": dict(sorted(coverage.items())),
        "universe_score_sources": dict(sorted(score_sources.items())),
        "universe_evidence_status": dict(sorted(evidence_status.items())),
        "top50_status": dict(sorted(top_status.items())),
        "top50_score_sources": dict(sorted(top_score_sources.items())),
        "top50_evidence_status": dict(sorted(top_evidence.items())),
        "registry_evidence_quality": dict(sorted(evidence_quality.items())),
        "official_core_shadow_impact": shadow_impact,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("Sector Taxonomy registry gate failed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "contracts" / "registries" / "sector_registry.json"
UNIVERSE = ROOT / "docs" / "data" / "universe.json"
CLOSE = ROOT / "docs" / "data" / "close.json"

from scripts.sector_groups import (
    CODE_TO_RECORD,
    OFFICIAL_INDUSTRY_CAN_GRANT_FULL_CORE_SCORE,
    PRIMARY_GROUP_MIN_CONFIDENCE,
    PRIMARY_GROUP_MIN_PEERS,
    SECONDARY_GROUP_MIN_CONFIDENCE,
    TAXONOMY_VERSION,
    classification_for,
    taxonomy_stats,
)


def load(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"sector registry gate: invalid JSON {path}: {exc}")


def main():
    registry = load(REGISTRY, {})
    errors = []
    warnings = []
    seen = {}
    registry_evidence = Counter()

    if not isinstance(registry, dict):
        raise SystemExit("Sector Taxonomy registry must be an object")
    if str(registry.get("taxonomy_version") or "") != TAXONOMY_VERSION:
        errors.append(
            f"version mismatch registry={registry.get('taxonomy_version')} resolver={TAXONOMY_VERSION}"
        )
    if OFFICIAL_INDUSTRY_CAN_GRANT_FULL_CORE_SCORE:
        errors.append("official industry may not grant full narrow-sector score")

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
        registry_evidence[quality] += 1
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
    unclassified_codes = []
    if isinstance(universe, list):
        for row in universe:
            if not isinstance(row, dict):
                continue
            c = classification_for(row.get("code"), name=row.get("name"), industry=row.get("industry"))
            coverage[c["classification_status"]] += 1
            score_sources[c["score_source"]] += 1
            evidence_status[c["evidence_status"]] += 1
            if c["classification_status"] == "UNCLASSIFIED":
                unclassified_codes.append(str(row.get("code") or ""))
            if c["score_source"] == "PRIMARY_GROUP" and not c.get("primary_group"):
                errors.append(f"{row.get('code')}: PRIMARY_GROUP score source without primary group")
            if c["score_source"] == "OFFICIAL_PROXY" and c.get("core_sector_score_eligible"):
                errors.append(f"{row.get('code')}: official proxy incorrectly core-score eligible")
        if universe and unclassified_codes:
            errors.append(
                f"universe has {len(unclassified_codes)} truly UNCLASSIFIED stocks: "
                + ",".join(unclassified_codes[:20])
            )

    close = load(CLOSE, {})
    close_rows = (close.get("rows") or []) if isinstance(close, dict) else []
    top = close_rows[:50]
    top_status = Counter()
    top_score_sources = Counter()
    top_evidence = Counter()
    top_unclassified = []
    top_curated_only = []
    for row in top:
        c = classification_for(row.get("code"), name=row.get("name"), industry=row.get("industry"))
        top_status[c["classification_status"]] += 1
        top_score_sources[c["score_source"]] += 1
        top_evidence[c["evidence_status"]] += 1
        if c["classification_status"] == "UNCLASSIFIED":
            top_unclassified.append(str(row.get("code") or ""))
        if c["evidence_status"] == "CURATED_ONLY":
            top_curated_only.append({
                "code": str(row.get("code") or ""),
                "name": row.get("name"),
                "primary_group": c.get("primary_group"),
                "confidence": c.get("primary_group_confidence"),
            })
    if top_unclassified:
        errors.append("top ranking pool contains UNCLASSIFIED: " + ",".join(top_unclassified))

    # Critical score-integrity rule: official-industry evidence is valuable for
    # identity/fallback display but must never silently become the full narrow
    # sector component. Any future code that invents such a source fails here.
    forbidden_full_sources = [k for k in score_sources if k not in {"PRIMARY_GROUP", "OFFICIAL_PROXY", "NONE"}]
    if forbidden_full_sources:
        errors.append("unexpected sector score sources: " + ",".join(sorted(forbidden_full_sources)))

    stats = taxonomy_stats()
    report = {
        "status": "FAIL" if errors else "PASS",
        "taxonomy_version": TAXONOMY_VERSION,
        "registry_entries": stats.get("registry_entries"),
        "eligible_registry_primary_codes": stats.get("eligible_primary_codes"),
        "registry_primary_groups": stats.get("primary_groups"),
        "official_industry_can_grant_full_core_score": OFFICIAL_INDUSTRY_CAN_GRANT_FULL_CORE_SCORE,
        "universe_rows": len(universe) if isinstance(universe, list) else 0,
        "universe_status": dict(sorted(coverage.items())),
        "universe_score_sources": dict(sorted(score_sources.items())),
        "universe_evidence_status": dict(sorted(evidence_status.items())),
        "top50_status": dict(sorted(top_status.items())),
        "top50_score_sources": dict(sorted(top_score_sources.items())),
        "top50_evidence_status": dict(sorted(top_evidence.items())),
        "top50_curated_only": top_curated_only,
        "registry_evidence_quality": dict(sorted(registry_evidence.items())),
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("Sector Taxonomy registry gate failed")


if __name__ == "__main__":
    main()

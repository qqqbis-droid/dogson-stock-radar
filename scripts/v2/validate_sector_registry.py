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
    evidence_quality = Counter()

    if not isinstance(registry, dict):
        raise SystemExit("Sector Taxonomy registry must be an object")
    if str(registry.get("taxonomy_version") or "") != TAXONOMY_VERSION:
        errors.append(
            f"version mismatch registry={registry.get('taxonomy_version')} resolver={TAXONOMY_VERSION}"
        )

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
    unclassified_codes = []
    if isinstance(universe, list):
        for row in universe:
            if not isinstance(row, dict):
                continue
            c = classification_for(
                row.get("code"), name=row.get("name"), industry=row.get("industry")
            )
            coverage[c["classification_status"]] += 1
            if c["classification_status"] == "UNCLASSIFIED":
                unclassified_codes.append(str(row.get("code") or ""))
        if universe and unclassified_codes:
            errors.append(
                f"universe has {len(unclassified_codes)} truly UNCLASSIFIED stocks: "
                + ",".join(unclassified_codes[:20])
            )

    close = load(CLOSE, {})
    top = (close.get("rows") or [])[:50] if isinstance(close, dict) else []
    top_status = Counter()
    top_unclassified = []
    for row in top:
        c = classification_for(
            row.get("code"), name=row.get("name"), industry=row.get("industry")
        )
        top_status[c["classification_status"]] += 1
        if c["classification_status"] == "UNCLASSIFIED":
            top_unclassified.append(str(row.get("code") or ""))
    if top_unclassified:
        errors.append("top ranking pool contains UNCLASSIFIED: " + ",".join(top_unclassified))

    stats = taxonomy_stats()
    report = {
        "status": "FAIL" if errors else "PASS",
        "taxonomy_version": TAXONOMY_VERSION,
        "registry_entries": stats.get("registry_entries"),
        "eligible_primary_codes": stats.get("eligible_primary_codes"),
        "primary_groups": stats.get("primary_groups"),
        "universe_rows": len(universe) if isinstance(universe, list) else 0,
        "universe_status": dict(sorted(coverage.items())),
        "top50_status": dict(sorted(top_status.items())),
        "evidence_quality": dict(sorted(evidence_quality.items())),
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("Sector Taxonomy registry gate failed")


if __name__ == "__main__":
    main()

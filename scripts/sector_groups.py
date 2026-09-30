# -*- coding: utf-8 -*-
"""犬子老師雷達 Sector Taxonomy registry-backed resolver.

Single source of truth:
    contracts/registries/sector_registry.json
    contracts/registries/taxonomy_registry.json

Classification confidence and evidence provenance are separate:
- registry primary groups may pass structural scoring gates while their external
  evidence status is still CURATED_ONLY;
- official TWSE/TPEx industry is OFFICIAL_DIRECT evidence for broad industry
  membership, but NEVER grants full narrow-sector score by itself;
- stock-specific review/evidence overrides generic official-industry evidence;
- secondary/theme tags never stack core sector points;
- duplicate registry primary membership fails closed.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "contracts" / "registries" / "sector_registry.json"
POLICY_PATH = ROOT / "contracts" / "registries" / "taxonomy_registry.json"

INDUSTRY_NAMES = {
    "01":"水泥工業","02":"食品工業","03":"塑膠工業","04":"紡織纖維","05":"電機機械","06":"電器電纜",
    "08":"玻璃陶瓷","09":"造紙工業","10":"鋼鐵工業","11":"橡膠工業","12":"汽車工業","14":"建材營造",
    "15":"航運業","16":"觀光餐旅","17":"金融保險","18":"貿易百貨","19":"綜合","20":"其他","21":"化學工業",
    "22":"生技醫療","23":"油電燃氣","24":"半導體業","25":"電腦及週邊設備業","26":"光電業","27":"通信網路業",
    "28":"電子零組件業","29":"電子通路業","30":"資訊服務業","31":"其他電子業","32":"文化創意","33":"農業科技",
    "34":"電子商務","35":"綠能環保","36":"數位雲端","37":"運動休閒","38":"居家生活"
}
INDUSTRY_CODES_BY_NAME = {v: k for k, v in INDUSTRY_NAMES.items()}


def _load_json(path: Path, expected_type):
    if not path.is_file():
        raise RuntimeError(f"Sector Taxonomy required file missing: {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Sector Taxonomy invalid JSON: {path}: {exc}") from exc
    if not isinstance(obj, expected_type):
        raise RuntimeError(f"Sector Taxonomy wrong JSON type: {path}")
    return obj


_POLICY = _load_json(POLICY_PATH, dict)
TAXONOMY_VERSION = str(_POLICY.get("taxonomy_version") or "UNKNOWN")
_CLASS_POLICY = _POLICY.get("classification_policy") or {}
PRIMARY_GROUP_MIN_CONFIDENCE = float(_CLASS_POLICY.get("primary_group_min_confidence", 80))
SECONDARY_GROUP_MIN_CONFIDENCE = float(_CLASS_POLICY.get("secondary_group_min_confidence", 70))
PRIMARY_GROUP_MIN_PEERS = int(_CLASS_POLICY.get("primary_group_min_peers", 3))
OFFICIAL_INDUSTRY_CAN_GRANT_FULL_CORE_SCORE = bool(
    _CLASS_POLICY.get("official_industry_can_grant_full_core_score", False)
)
REVIEW_DAYS = int(_CLASS_POLICY.get("review_days", 180))

_REGISTRY = _load_json(REGISTRY_PATH, dict)
if str(_REGISTRY.get("taxonomy_version") or "") != TAXONOMY_VERSION:
    raise RuntimeError(
        f"Sector Taxonomy version mismatch registry={_REGISTRY.get('taxonomy_version')} policy={TAXONOMY_VERSION}"
    )

CODE_TO_RECORD = {}
_group_members = defaultdict(list)
for grow in _REGISTRY.get("groups") or []:
    if not isinstance(grow, dict):
        raise RuntimeError("Sector Taxonomy group row must be object")
    group = str(grow.get("group") or "").strip()
    if not group:
        raise RuntimeError("Sector Taxonomy group missing name")
    try:
        confidence = float(grow.get("confidence"))
    except Exception as exc:
        raise RuntimeError(f"Sector Taxonomy group {group} missing confidence") from exc
    for raw_code in grow.get("members") or []:
        code = str(raw_code or "").strip()
        if not code:
            raise RuntimeError(f"Sector Taxonomy group {group} contains empty code")
        if code in CODE_TO_RECORD:
            raise RuntimeError(
                f"Sector Taxonomy {TAXONOMY_VERSION} duplicate primary code "
                f"{code}: {CODE_TO_RECORD[code].get('primary_group')} vs {group}"
            )
        CODE_TO_RECORD[code] = {
            "code": code,
            "primary_group": group,
            "primary_group_confidence": confidence,
            "secondary_groups": [],
            "theme_tags": [],
            "supply_chain_role": [group],
            "evidence_quality": grow.get("evidence_quality") or "UNSPECIFIED",
            "evidence_urls_or_refs": list(grow.get("evidence_urls_or_refs") or []),
            "classification_reason": grow.get("classification_reason"),
            "last_reviewed_at": grow.get("last_reviewed_at") or _REGISTRY.get("last_reviewed_at"),
            "review_due_at": grow.get("review_due_at") or _REGISTRY.get("review_due_at"),
            "revenue_evidence_period": grow.get("revenue_evidence_period"),
            "exposure_pct": grow.get("exposure_pct"),
        }
        _group_members[group].append(code)


def _blank_record(code):
    return {
        "code": code,
        "primary_group": None,
        "primary_group_confidence": None,
        "secondary_groups": [],
        "theme_tags": [],
        "supply_chain_role": [],
        "evidence_quality": "UNSPECIFIED",
        "evidence_urls_or_refs": [],
        "classification_reason": None,
        "last_reviewed_at": _REGISTRY.get("last_reviewed_at"),
        "review_due_at": _REGISTRY.get("review_due_at"),
        "revenue_evidence_period": None,
        "exposure_pct": None,
    }


for raw_code, override in (_REGISTRY.get("stock_overrides") or {}).items():
    code = str(raw_code or "").strip()
    if not code or not isinstance(override, dict):
        continue
    rec = CODE_TO_RECORD.setdefault(code, _blank_record(code))
    for key in (
        "primary_group","primary_group_confidence","secondary_groups","supply_chain_role",
        "evidence_quality","evidence_urls_or_refs","classification_reason",
        "last_reviewed_at","review_due_at","revenue_evidence_period","exposure_pct",
    ):
        if key in override:
            rec[key] = override[key]

for raw_code, tags in (_REGISTRY.get("theme_tags") or {}).items():
    code = str(raw_code or "").strip()
    if not code:
        continue
    rec = CODE_TO_RECORD.setdefault(code, _blank_record(code))
    rec["theme_tags"] = list(tags or [])

PRIMARY_GROUPS = {g: sorted(codes) for g, codes in sorted(_group_members.items())}
GROUP_SIZES = {g: len(codes) for g, codes in PRIMARY_GROUPS.items()}
CODE_TO_GROUP = {
    code: str(rec.get("primary_group") or "").strip()
    for code, rec in CODE_TO_RECORD.items()
    if str(rec.get("primary_group") or "").strip()
}
GROUP_CONFIDENCE = {}
for group, members in PRIMARY_GROUPS.items():
    vals = []
    for code in members:
        try:
            vals.append(float(CODE_TO_RECORD[code].get("primary_group_confidence")))
        except Exception:
            pass
    GROUP_CONFIDENCE[group] = min(vals) if vals else 0.0

SECONDARY_GROUPS = {
    code: [dict(x) for x in (rec.get("secondary_groups") or []) if isinstance(x, dict)]
    for code, rec in CODE_TO_RECORD.items() if rec.get("secondary_groups")
}
THEME_TAGS = {
    code: list(rec.get("theme_tags") or [])
    for code, rec in CODE_TO_RECORD.items() if rec.get("theme_tags")
}
SECONDARY_ONLY = {
    code for code, rec in CODE_TO_RECORD.items()
    if not str(rec.get("primary_group") or "").strip() and rec.get("secondary_groups")
}


def industry_name_for(industry):
    key = str(industry or "").strip()
    return INDUSTRY_NAMES.get(key, key if key and key != "nan" else "未分類")


def industry_code_for(industry):
    key = str(industry or "").strip()
    if key in INDUSTRY_NAMES:
        return key
    return INDUSTRY_CODES_BY_NAME.get(key)


def _confidence(value):
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def evidence_status_for(quality):
    q = str(quality or "UNSPECIFIED").upper()
    if q == "OFFICIAL_DIRECT":
        return "OFFICIAL_DIRECT"
    if q == "OFFICIAL_INDIRECT":
        return "OFFICIAL_SUPPORTED"
    if q == "CURATED_SEED":
        return "CURATED_ONLY"
    if q == "MULTI_BUSINESS_REVIEW":
        return "REVIEWED_MULTI_BUSINESS"
    return "NO_EXTERNAL_EVIDENCE"


def classification_for(code, name=None, industry=None):
    code = str(code or "").strip()
    rec = CODE_TO_RECORD.get(code) or {}
    official_code = industry_code_for(industry)
    official = industry_name_for(industry)
    group = str(rec.get("primary_group") or "").strip() or None
    conf = _confidence(rec.get("primary_group_confidence"))
    peer_count = int(GROUP_SIZES.get(group, 0)) if group else 0
    eligible = bool(
        group and conf is not None
        and conf >= PRIMARY_GROUP_MIN_CONFIDENCE
        and peer_count >= PRIMARY_GROUP_MIN_PEERS
    )

    if eligible:
        status, score_source = "VERIFIED", "PRIMARY_GROUP"
    elif group:
        status = "PROVISIONAL"
        score_source = "OFFICIAL_PROXY" if official != "未分類" else "NONE"
    elif official != "未分類":
        status, score_source = "OFFICIAL_ONLY", "OFFICIAL_PROXY"
    else:
        status, score_source = "UNCLASSIFIED", "NONE"

    secondary = []
    for item in rec.get("secondary_groups") or []:
        if not isinstance(item, dict):
            continue
        c = _confidence(item.get("confidence")) or 0
        if c >= SECONDARY_GROUP_MIN_CONFIDENCE and item.get("group"):
            secondary.append(dict(item))

    rec_quality = str(rec.get("evidence_quality") or "").strip()
    rec_refs = [str(x).strip() for x in (rec.get("evidence_urls_or_refs") or []) if str(x).strip()]
    has_stock_specific_evidence = rec_quality not in ("", "UNSPECIFIED", "NONE") or bool(rec_refs)
    if group or has_stock_specific_evidence:
        evidence_quality = rec_quality or "UNSPECIFIED"
        evidence_refs = rec_refs
    elif official != "未分類":
        evidence_quality = "OFFICIAL_DIRECT"
        evidence_refs = [f"TWSE/TPEx official industry code:{official_code or official}"]
    else:
        evidence_quality = "UNSPECIFIED"
        evidence_refs = []

    reason = rec.get("classification_reason")
    if not reason:
        if group:
            reason = (
                f"Taxonomy {TAXONOMY_VERSION} 主分類：{group}；"
                "已通過唯一性、信心與同儕樣本門檻。外部證據狀態另行標示。"
            )
        elif official != "未分類":
            reason = "官方產業已確認，但尚無足以取得完整窄族群分的 Primary；僅使用 capped proxy。"
        else:
            reason = "分類證據不足。"

    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "code": code,
        "name": str(name or code),
        "official_industry": official,
        "official_industry_code": official_code,
        "registry_primary_group": group,
        "primary_group": group,
        "primary_group_confidence": conf,
        "secondary_groups": secondary,
        "theme_tags": list(rec.get("theme_tags") or []),
        "supply_chain_role": list(rec.get("supply_chain_role") or ([group] if group else [])),
        "exposure_pct": rec.get("exposure_pct"),
        "revenue_evidence_period": rec.get("revenue_evidence_period"),
        "evidence_urls_or_refs": evidence_refs,
        "evidence_quality": evidence_quality,
        "evidence_status": evidence_status_for(evidence_quality),
        "last_reviewed_at": rec.get("last_reviewed_at") or _REGISTRY.get("last_reviewed_at"),
        "review_due_at": rec.get("review_due_at") or _REGISTRY.get("review_due_at"),
        "classification_status": status,
        "classification_reason": reason,
        "peer_count": peer_count,
        "score_source": score_source,
        "core_sector_score_eligible": eligible,
    }


def sector_group_for(code, name=None, industry=None):
    c = classification_for(code, name=name, industry=industry)
    return c["primary_group"] if c["core_sector_score_eligible"] else None


def sector_confidence_for(code, name=None, industry=None):
    return classification_for(code, name=name, industry=industry)["primary_group_confidence"]


def taxonomy_stats():
    statuses = Counter()
    evidence = Counter()
    eligible = 0
    primary_with_evidence = 0
    for code in CODE_TO_RECORD:
        c = classification_for(code)
        statuses[c["classification_status"]] += 1
        evidence[c["evidence_status"]] += 1
        if c["core_sector_score_eligible"]:
            eligible += 1
        if c["primary_group"] and c["evidence_urls_or_refs"]:
            primary_with_evidence += 1
    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "registry_path": str(REGISTRY_PATH.relative_to(ROOT)),
        "registry_entries": len(CODE_TO_RECORD),
        "primary_groups": len(PRIMARY_GROUPS),
        "eligible_primary_codes": eligible,
        "primary_codes_with_evidence": primary_with_evidence,
        "primary_group_min_confidence": PRIMARY_GROUP_MIN_CONFIDENCE,
        "secondary_group_min_confidence": SECONDARY_GROUP_MIN_CONFIDENCE,
        "primary_group_min_peers": PRIMARY_GROUP_MIN_PEERS,
        "official_industry_can_grant_full_core_score": OFFICIAL_INDUSTRY_CAN_GRANT_FULL_CORE_SCORE,
        "review_days": REVIEW_DAYS,
        "registry_statuses_without_runtime_industry": dict(sorted(statuses.items())),
        "evidence_status_counts": dict(sorted(evidence.items())),
        "group_sizes": dict(sorted(GROUP_SIZES.items())),
    }

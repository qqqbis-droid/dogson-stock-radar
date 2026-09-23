#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f"v1.5.2 patch missing marker: {label}")
    return text.replace(old, new, 1)


def patch_hourly_builder():
    p = "scripts/build_hourly.py"
    s = read(p)

    s = must_replace(
        s,
        "    rows = []\n    failed = []",
        "    rows = []  # strict 60K lifecycle candidates\n    all_rows = []  # every close-radar stock: calculated 60K or explicit unavailable status\n    failed = []",
        "row collections",
    )

    s = must_replace(
        s,
        "            if not (avg_turn_mn >= 50 and avg_vol_lots >= 300):\n                continue",
        "            liquidity_ok = bool(avg_turn_mn >= 50 and avg_vol_lots >= 300)",
        "liquidity no longer drops basic 60K row",
    )

    s = must_replace(
        s,
        "            # Nearby falling 240T overhead is a hard structural warning.\n            if (not above240) and overhead <= 3 and d240 != \"UP\":\n                continue",
        "            # Keep this as a candidate exclusion, but still publish the stock's 60K basics.\n            near_240_risk = bool((not above240) and overhead <= 3 and d240 != \"UP\")",
        "240T warning no longer drops basic row",
    )

    old_category = '''            category = None\n            if m20 <= m60 and -0.8 <= gap <= 0 and d20 == \"UP\" and d60 in (\"UP\", \"FLAT\"):\n                category = \"PRE_CROSS\"\n            elif m20 > m60 and cross_age is not None and cross_age <= 3 and d20 == \"UP\" and d60 in (\"UP\", \"FLAT\"):\n                category = \"EARLY\"\n            elif m20 > m60 and d20 == \"UP\" and d60 == \"UP\":\n                category = \"ACCEL_CONT\" if (s20 >= s60 and slope_diff > 0.60) else \"STABLE_CONT\"\n            else:\n                continue\n'''
    new_category = '''            category = None\n            if m20 <= m60 and -0.8 <= gap <= 0 and d20 == \"UP\" and d60 in (\"UP\", \"FLAT\"):\n                category = \"PRE_CROSS\"\n            elif m20 > m60 and cross_age is not None and cross_age <= 3 and d20 == \"UP\" and d60 in (\"UP\", \"FLAT\"):\n                category = \"EARLY\"\n            elif m20 > m60 and d20 == \"UP\" and d60 == \"UP\":\n                category = \"ACCEL_CONT\" if (s20 >= s60 and slope_diff > 0.60) else \"STABLE_CONT\"\n\n            candidate = bool(category is not None and liquidity_ok and not near_240_risk)\n            exclusion_reason = \"\"\n            if not liquidity_ok:\n                exclusion_reason = f\"流動性不足：10日均額{avg_turn_mn:.0f}百萬／均量{avg_vol_lots:.0f}張\"\n            elif near_240_risk:\n                exclusion_reason = \"240T近壓且斜率未向上\"\n            elif category is None:\n                if m20 <= m60 and d20 != \"UP\":\n                    exclusion_reason = \"60K 20T仍在60T下方，且20T尚未轉上\"\n                elif m20 <= m60:\n                    exclusion_reason = \"60K 20T仍在60T下方，未達金叉前夕門檻\"\n                elif d20 != \"UP\" or d60 not in (\"UP\", \"FLAT\"):\n                    exclusion_reason = \"20T／60T斜率未形成同步向上\"\n                else:\n                    exclusion_reason = \"未符合金叉前夕／初升／續航生命週期條件\"\n'''
    s = must_replace(s, old_category, new_category, "category candidate split")

    old_score = '''            score = 0\n            score += 12 if d20 == \"UP\" else 0\n            score += 10 if d60 == \"UP\" else (5 if d60 == \"FLAT\" else 0)\n            score += 3 if m20 > m60 else 1\n            score += 8 if category == \"PRE_CROSS\" else (12 if category == \"EARLY\" else 15)\n            score += 10 if above240 else (4 if overhead > 5 else 2)\n            score += 8 if d240 == \"UP\" else (5 if d240 == \"FLAT\" else 2)\n            score += 2 if orderly else 0\n            score += 10 if slope_diff <= 0.30 else (8 if slope_diff <= 0.60 else (6 if slope_diff <= 1.20 else (3 if slope_diff <= 2 else 1)))\n            ap = abs(p20)\n            score += 15 if ap <= 3 else (12 if ap <= 5 else (7 if ap <= 8 else (3 if ap <= 12 else 1)))\n            if category == \"PRE_CROSS\":\n                ag = abs(gap)\n                score += 10 if ag <= 0.30 else (8 if ag <= 0.80 else 3)\n            else:\n                score += 10 if 0 <= gap <= 3 else (6 if 3 < gap <= 6 else 2)\n            score += 2 if volratio is None else (5 if 0.8 <= volratio <= 2.5 else (3 if 0.5 <= volratio < 0.8 or 2.5 < volratio <= 4 else 1))\n            score = min(100, int(score))\n'''
    new_score = '''            # Only lifecycle matches receive the legacy candidate score.\n            # Non-candidates still publish MA/slope/cross/extension data for every close card.\n            score = None\n            if category is not None:\n                score = 0\n                score += 12 if d20 == \"UP\" else 0\n                score += 10 if d60 == \"UP\" else (5 if d60 == \"FLAT\" else 0)\n                score += 3 if m20 > m60 else 1\n                score += 8 if category == \"PRE_CROSS\" else (12 if category == \"EARLY\" else 15)\n                score += 10 if above240 else (4 if overhead > 5 else 2)\n                score += 8 if d240 == \"UP\" else (5 if d240 == \"FLAT\" else 2)\n                score += 2 if orderly else 0\n                score += 10 if slope_diff <= 0.30 else (8 if slope_diff <= 0.60 else (6 if slope_diff <= 1.20 else (3 if slope_diff <= 2 else 1)))\n                ap = abs(p20)\n                score += 15 if ap <= 3 else (12 if ap <= 5 else (7 if ap <= 8 else (3 if ap <= 12 else 1)))\n                if category == \"PRE_CROSS\":\n                    ag = abs(gap)\n                    score += 10 if ag <= 0.30 else (8 if ag <= 0.80 else 3)\n                else:\n                    score += 10 if 0 <= gap <= 3 else (6 if 3 < gap <= 6 else 2)\n                score += 2 if volratio is None else (5 if 0.8 <= volratio <= 2.5 else (3 if 0.5 <= volratio < 0.8 or 2.5 < volratio <= 4 else 1))\n                score = min(100, int(score))\n'''
    s = must_replace(s, old_score, new_score, "candidate score block")

    s = must_replace(
        s,
        "            combined = round(score * 0.50 + dpos + chip * 0.80 + sector, 1)",
        "            combined = round(score * 0.50 + dpos + chip * 0.80 + sector, 1) if score is not None else None",
        "combined optional",
    )

    s = must_replace(s, "            rows.append({", "            row = {", "row object")
    s = must_replace(
        s,
        '                "category60": category,\n                "score60": score,',
        '                "category60": category,\n                "is_candidate": candidate,\n                "data_status": "OK",\n                "exclusion_reason": exclusion_reason,\n                "score60": score,',
        "row candidate metadata",
    )
    s = must_replace(
        s,
        '                "existing_radar_score": cr.get("score"),\n            })\n        time.sleep(0.25)',
        '                "existing_radar_score": cr.get("score"),\n            }\n            all_rows.append(row)\n            if candidate:\n                rows.append(row)\n        time.sleep(0.25)',
        "append all and candidate rows",
    )

    marker = '    light_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}\n'
    filler = '''    # Ensure every close-radar stock has an explicit 60K card state, even when Yahoo\n    # cannot supply 246 completed 60-minute bars.\n    covered_codes = {str(r.get("code")) for r in all_rows}\n    for sym, m in meta.items():\n        code = str(m.get("code"))\n        if code in covered_codes:\n            continue\n        all_rows.append({\n            **m,\n            "category60": None,\n            "is_candidate": False,\n            "data_status": "UNAVAILABLE",\n            "exclusion_reason": "60K資料不足或來源未回傳（需要至少246根完成K棒）",\n            "score60": None,\n            "combined_score": None,\n            "entry_light": None,\n            "entry_light_emoji": "⚪",\n            "entry_light_label": "資料待補",\n        })\n\n'''
    if filler.strip() not in s:
        s = must_replace(s, marker, filler + marker, "all-row placeholders")

    s = must_replace(
        s,
        '        "method": "60K lifecycle + independent entry-position light; review score = 60K 50% + daily position 20% + chips 20% + sector 10%",',
        '        "method": "all close stocks publish 60K basics; lifecycle candidates remain strict; candidate review score = 60K 50% + daily position 20% + chips 20% + sector 10%",',
        "method description",
    )
    s = must_replace(
        s,
        '        "failed_60m": len(set(failed)),\n        "rows": rows,',
        '        "failed_60m": len(set(failed)),\n        "candidate_count": len(rows),\n        "all_row_count": len(all_rows),\n        "calculated_60k_count": sum(1 for r in all_rows if r.get("data_status") == "OK"),\n        "rows": rows,\n        "all_rows": all_rows,',
        "result all_rows",
    )
    s = s.replace(
        '    print("hourly done", len(rows), counts, lights, "failed", len(set(failed)))',
        '    print("hourly done candidates", len(rows), "all", len(all_rows), counts, lights, "failed", len(set(failed)))',
        1,
    )
    write(p, s)


def patch_hourly_ui():
    p = "docs/hourly.js"
    s = read(p)
    s = s.replace("｜60K趨勢＋進場燈號", "｜60K全股票資訊＋候選燈號", 1)
    s = must_replace(
        s,
        "      `<div class=\"hourlysummary\">符合 ${data.rows?.length||0} 檔｜🟢位置舒服 ${counts.GREEN||0}｜收合時不占版面，點「展開」再挑60K股票。</div>`;",
        "      `<div class=\"hourlysummary\">候選 ${data.rows?.length||0} 檔｜60K可計算 ${data.calculated_60k_count||0}/${data.all_row_count||0} 檔｜🟢位置舒服 ${counts.GREEN||0}｜每張盤後卡都會顯示60K狀態。</div>`;",
        "collapsed summary",
    )
    s = must_replace(
        s,
        "      <div class=\"hourlymore\">目前共 ${data.rows?.length||0} 檔符合60K生命週期條件；🟢 ${counts.GREEN||0}｜🟡 ${counts.YELLOW||0}｜🟠 ${counts.ORANGE||0}｜🔴 ${counts.RED||0}。點股票會帶到下方完整卡片。</div>`:",
        "      <div class=\"hourlymore\">候選 ${data.rows?.length||0} 檔；全盤後卡60K覆蓋 ${data.calculated_60k_count||0}/${data.all_row_count||0} 檔。🟢 ${counts.GREEN||0}｜🟡 ${counts.YELLOW||0}｜🟠 ${counts.ORANGE||0}｜🔴 ${counts.RED||0}。未進候選的股票仍會在個股卡顯示20T/60T/240T與原因。</div>`:",
        "expanded summary",
    )
    s = must_replace(
        s,
        "      <div class=\"hourlytop\"><div><div class=\"hourlytitle\">⏱️ 60分K 趨勢雷達</div><div class=\"hourlysub\">四種生命週期＋進場燈號；預設收合，避免手機版被名單擋住。</div></div><div style=\"display:flex;gap:8px;align-items:flex-start\"><div class=\"hourlystamp\">${data.trade_date||''}<br>${updated}</div><button id=\"hourlyToggle\" class=\"hourlytoggle\">${hourlyExpanded?'收合 ▲':'展開 ▼'}</button></div></div>",
        "      <div class=\"hourlytop\"><div><div class=\"hourlytitle\">⏱️ 60分K 趨勢雷達</div><div class=\"hourlysub\">每檔盤後股票都有60K狀態；只有符合四種生命週期才進候選名單。預設收合。</div></div><div style=\"display:flex;gap:8px;align-items:flex-start\"><div class=\"hourlystamp\">${data.trade_date||''}<br>${updated}</div><button id=\"hourlyToggle\" class=\"hourlytoggle\">${hourlyExpanded?'收合 ▲':'展開 ▼'}</button></div></div>",
        "panel explanation",
    )

    old_decorate = '''    document.querySelectorAll('.card').forEach(card=>{\n      const r=byCode.get(codeFromCard(card));if(!r)return;\n      const l=life(r);\n      const strip=document.createElement('div');strip.className='hourlystrip';\n      strip.title=r.entry_light_reason||'';\n      strip.innerHTML=`<div class=\"hourlystriptop\"><div class=\"hourlylifelabel\">${l.emoji} ${l.label}｜60K ${n(r.score60,0)}</div><div class=\"hourlyentry\">${r.entry_light_emoji||''} ${r.entry_light_label||''}</div></div><div class=\"hourlystripmeta\">20T${DIR[r.dir20]||'—'} ${n(r.ma20_60,2)}｜60T${DIR[r.dir60]||'—'} ${n(r.ma60_60,2)}｜240T${DIR[r.dir240]||'—'} ${n(r.ma240_60,2)}<br>${crossText(r)}｜斜率差 ${n(r.slope_diff,3)}pp｜距60K20T ${signed(r.price_vs20_60_pct,2)}${r.entry_light_reason?'｜'+r.entry_light_reason:''}</div>`;\n      const top=card.querySelector('.top');if(top)top.insertAdjacentElement('afterend',strip);else card.prepend(strip);\n    });'''
    new_decorate = '''    document.querySelectorAll('.card').forEach(card=>{\n      const code=codeFromCard(card);\n      const r=byCode.get(code);\n      const strip=document.createElement('div');strip.className='hourlystrip';\n      if(!r||r.data_status==='UNAVAILABLE'){\n        const reason=r?.exclusion_reason||'60K資料尚未建立';\n        strip.innerHTML=`<div class=\"hourlystriptop\"><div class=\"hourlylifelabel\">⚪ 60K資料待補</div><div class=\"hourlyentry\">未進候選</div></div><div class=\"hourlystripmeta\">${reason}</div>`;\n      }else{\n        const l=life(r);\n        const status=r.is_candidate?`${l.emoji} ${l.label}｜60K ${n(r.score60,0)}`:'⚪ 未進60K候選';\n        const right=r.is_candidate?`${r.entry_light_emoji||''} ${r.entry_light_label||''}`:'結構資訊照常顯示';\n        const reason=!r.is_candidate&&r.exclusion_reason?`<br>未進候選：${r.exclusion_reason}`:'';\n        strip.title=r.entry_light_reason||r.exclusion_reason||'';\n        strip.innerHTML=`<div class=\"hourlystriptop\"><div class=\"hourlylifelabel\">${status}</div><div class=\"hourlyentry\">${right}</div></div><div class=\"hourlystripmeta\">20T${DIR[r.dir20]||'—'} ${n(r.ma20_60,2)}｜60T${DIR[r.dir60]||'—'} ${n(r.ma60_60,2)}｜240T${DIR[r.dir240]||'—'} ${n(r.ma240_60,2)}<br>${crossText(r)}｜斜率差 ${n(r.slope_diff,3)}pp｜距60K20T ${signed(r.price_vs20_60_pct,2)}${r.entry_light_reason?'｜'+r.entry_light_reason:''}${reason}</div>`;\n      }\n      const top=card.querySelector('.top');if(top)top.insertAdjacentElement('afterend',strip);else card.prepend(strip);\n    });'''
    s = must_replace(s, old_decorate, new_decorate, "decorate every close card")
    s = must_replace(
        s,
        "      byCode=new Map((data.rows||[]).map(x=>[String(x.code),x]));",
        "      byCode=new Map(((data.all_rows&&data.all_rows.length)?data.all_rows:(data.rows||[])).map(x=>[String(x.code),x]));",
        "all rows lookup",
    )
    write(p, s)


def patch_index_and_cache():
    p = "docs/index.html"
    s = read(p)
    s = s.replace(
        "Free Edition v1.5.1｜盤中動能100＋盤後波段直接100＋可展開族群",
        "Free Edition v1.5.2｜盤中動能100＋盤後波段100＋60K全股票資訊",
        1,
    )
    s = re.sub(r'hourly\.js\?v=\d+', 'hourly.js?v=152', s)
    write(p, s)

    p = "docs/sw.js"
    s = read(p)
    s = s.replace("const CACHE='dogson-free-v151';", "const CACHE='dogson-free-v152';", 1)
    write(p, s)


def main():
    patch_hourly_builder()
    patch_hourly_ui()
    patch_index_and_cache()
    print("v1.5.2 full 60K coverage patch applied")


if __name__ == "__main__":
    main()

# 2026-09-23 60m Radar V5 entry-light test

Research branch only; live radar is unchanged.

Entry-position light is separate from trend/quality scoring. Base rule uses price distance to the 60-minute 20T, then daily overextension can downgrade the light:
- GREEN: -1.5% to +2.0% vs 60K 20T
- YELLOW: +2% to +5%, or -1.5% to -3%
- ORANGE: +5% to +8%
- RED: >+8% or <-3%
- Daily dist20 >8%, 5-day return >10%, or RSI >72 can downgrade to ORANGE; more severe daily extension can downgrade to RED.

Scan snapshot: 2026-09-23 00:21:30 +08:00. Lifecycle counts: PRE_CROSS 4, EARLY 12, STABLE_CONT 56, ACCEL_CONT 114. Entry-light counts: GREEN 49, YELLOW 23, ORANGE 41, RED 73.

Examples from the balanced shortlist:
- 6239 力成: ACCEL_CONT, combined 89.5, 60K score 87, GREEN. Price +1.57% vs 60K20T.
- 3014 聯陽: ACCEL_CONT, combined 87.0, 60K score 92, GREEN. Price +1.60% vs 60K20T.
- 3005 神基: STABLE_CONT, combined 84.8, 60K score 100, GREEN. Price +0.28% vs 60K20T.
- 1609 大亞: STABLE_CONT, combined 84.5, 60K score 97, GREEN. Price +0.24% vs 60K20T.
- 2609 陽明: STABLE_CONT, combined 84.0, 60K score 96, GREEN. Price -0.57% vs 60K20T.
- 5269 祥碩: STABLE_CONT, combined 83.9, 60K score 89, GREEN. Price -0.57% vs 60K20T.
- 2885 元大金: EARLY, combined 79.9, 60K score 95, GREEN. Price +0.96% vs 60K20T.
- 1102 亞泥: EARLY, combined 79.2, 60K score 92, GREEN. Price +0.65% vs 60K20T.
- 1514 亞力: EARLY, combined 78.5, 60K score 85, GREEN. Price +0.22% vs 60K20T.
- 6005 群益證: EARLY, combined 70.1, 60K score 85, GREEN. Price +1.68% vs 60K20T.
- 2316 楠梓電: PRE_CROSS, combined 66.7, 60K score 81, GREEN. Price +1.98% vs 60K20T.
- 6789 采鈺: PRE_CROSS, combined 67.1, 60K score 69, YELLOW. Price +2.93% vs 60K20T.
- 3653 健策: EARLY, combined 73.8, 60K score 78, YELLOW. Price +4.03% vs 60K20T.
- 6510 精測: PRE_CROSS, combined 57.8, 60K score 70, ORANGE. Price +7.44% vs 60K20T.

Interpretation: the light is an entry-position/extension indicator, not a buy/sell signal. It should be displayed alongside lifecycle bucket, 60K structural score, chips and sector context.
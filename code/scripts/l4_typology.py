#!/usr/bin/env python3
"""
L4 decoupling typology (ENT attention-burden census).

Implements exactly the rule table frozen in L4_分型规则表_2026-11-12.md,
which operationalises the type names/definitions frozen in the user-signed
work report v1 section 4-L4. The signed report froze type names, definitions
and the three-signal framework but no numeric thresholds; the thresholds
below are the production-stage operationalisation recorded in the rule table
(landed before this run) and are reported with two sensitivity threshold
sets. The typology is a descriptive classification, not a preregistered
inference.

Signals (first period 1995-1999 vs last period; last-period burden side
2020-23 per amendment v1.1):
  S = relative change of L1 publication share (14-area pool)
  B = relative change of GBD DALY share (7-cause pool, from frozen ABR table)
  A = change of log2 ABR
Main thresholds: share +/-25%, log2 ABR +/-0.5.
Sensitivity sets: low (+/-15%, +/-0.3), high (+/-35%, +/-0.7).

Assignment order (burden tier): (1) S down & B down -> resolution-dilution;
(2) S up & B in {stable, down} & A up -> technology-ignited; (3) all stable
-> constant; (4) S and B same direction & A stable -> burden-tracking;
(5) otherwise unclassified (reported as such, never forced).
Attention tier (no GBD cause, per signed report section 3): share-dynamics
labels only, no burden typology.

Outputs: data_l4/signals.csv, data_l4/typology.csv
"""

import csv
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L1_CSV = os.path.join(ROOT, "data_l1", "l1_counts_by_year.csv")
ABR_CSV = os.path.join(ROOT, "data_l2", "abr", "abr_primary.csv")
OUT_DIR = os.path.join(ROOT, "data_l4")

BURDEN_AREAS = [
    "otitis_media", "hearing_loss", "larynx_cancer", "oral_cancer",
    "nasopharynx_cancer", "other_pharynx_cancer", "thyroid_cancer",
]
FIRST, LAST = "1995-1999", "2020-2024"
FIRST_YEARS, LAST_YEARS = range(1995, 2000), range(2020, 2025)

SETS = {  # name: (share_pct_threshold, log2_threshold)
    "low": (15.0, 0.3),
    "main": (25.0, 0.5),
    "high": (35.0, 0.7),
}


def direction(rel_pct, thr):
    if rel_pct >= thr:
        return "up"
    if rel_pct <= -thr:
        return "down"
    return "stable"


def direction_log2(delta, thr):
    if delta >= thr:
        return "up"
    if delta <= -thr:
        return "down"
    return "stable"


def assign(s, b, a):
    if s == "down" and b == "down":
        return "resolution_dilution"
    if s == "up" and b in ("stable", "down") and a == "up":
        return "technology_ignited"
    if s == "stable" and b == "stable" and a == "stable":
        return "constant"
    if s == b and s in ("up", "down") and a == "stable":
        return "burden_tracking"
    return "unclassified"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    l1 = defaultdict(dict)
    with open(L1_CSV) as f:
        for r in csv.DictReader(f):
            l1[r["area"]][int(r["year"])] = int(r["count"])
    areas = sorted(l1)

    def pool_total(years, subset=None):
        return sum(l1[a][y] for a in (subset or areas) for y in years)

    abr = {}
    with open(ABR_CSV) as f:
        for r in csv.DictReader(f):
            abr[(r["area"], r["period"])] = r

    signals, typology = [], []
    for area in areas:
        pf = sum(l1[area][y] for y in FIRST_YEARS)
        pl = sum(l1[area][y] for y in LAST_YEARS)
        sf = pf / pool_total(FIRST_YEARS)
        sl = pl / pool_total(LAST_YEARS)
        s_rel = (sl / sf - 1) * 100
        row = {
            "area": area,
            "tier": "burden" if area in BURDEN_AREAS else "attention",
            "pub_n_first": pf, "pub_n_last": pl,
            "pub_share14_first": f"{sf:.6f}", "pub_share14_last": f"{sl:.6f}",
            "S_rel_pct": f"{s_rel:.2f}",
        }
        types = {}
        if area in BURDEN_AREAS:
            bf = float(abr[(area, FIRST)]["burden_share_pool"])
            bl = float(abr[(area, LAST)]["burden_share_pool"])
            b_rel = (bl / bf - 1) * 100
            af = float(abr[(area, FIRST)]["log2_abr"])
            al = float(abr[(area, LAST)]["log2_abr"])
            a_delta = al - af
            # annualised DALY context (first period 5 burden-years, last 4)
            daly_f = float(abr[(area, FIRST)]["burden_global"]) / 5
            daly_l = float(abr[(area, LAST)]["burden_global"]) / 4
            row.update({
                "daly_share_first": f"{bf:.6f}", "daly_share_last": f"{bl:.6f}",
                "B_rel_pct": f"{b_rel:.2f}",
                "log2abr_first": f"{af:.6f}", "log2abr_last": f"{al:.6f}",
                "A_delta": f"{a_delta:.6f}",
                "daly_annual_pct_change": f"{(daly_l / daly_f - 1) * 100:.2f}",
            })
            for name, (sthr, athr) in SETS.items():
                types[name] = assign(direction(s_rel, sthr),
                                     direction(b_rel, sthr),
                                     direction_log2(a_delta, athr))
            row.update({
                "S_dir_main": direction(s_rel, SETS["main"][0]),
                "B_dir_main": direction(b_rel, SETS["main"][0]),
                "A_dir_main": direction_log2(a_delta, SETS["main"][1]),
            })
        else:
            for name, (sthr, _) in SETS.items():
                d = direction(s_rel, sthr)
                types[name] = {"up": "share_rising", "stable": "share_stable",
                               "down": "share_falling"}[d]
            row.update({"S_dir_main": direction(s_rel, SETS["main"][0]),
                        "B_dir_main": "", "A_dir_main": ""})
        signals.append(row)
        typology.append({
            "area": area, "tier": row["tier"],
            "type_main": types["main"], "type_low": types["low"],
            "type_high": types["high"],
            "robust_across_thresholds":
                "1" if types["low"] == types["main"] == types["high"] else "0",
        })

    for rows, path in ((signals, os.path.join(OUT_DIR, "signals.csv")),
                       (typology, os.path.join(OUT_DIR, "typology.csv"))):
        fields = list(dict.fromkeys(k for r in rows for k in r))
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    print("area            tier      S%      B%    dlog2ABR  S/B/A(main)        main                low                 high                robust")
    for s, t in zip(signals, typology):
        print(f"{s['area']:<22}{s['tier']:<9}{s['S_rel_pct']:>7} "
              f"{s.get('B_rel_pct', ''):>7} {s.get('A_delta', ''):>9}  "
              f"{s['S_dir_main']}/{s['B_dir_main'] or '-'}/{s['A_dir_main'] or '-':<10} "
              f"{t['type_main']:<20}{t['type_low']:<20}{t['type_high']:<20}{t['robust_across_thresholds']}")


if __name__ == "__main__":
    main()

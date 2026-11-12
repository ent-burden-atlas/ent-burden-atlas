#!/usr/bin/env python3
"""
Terminology-drift sensitivity verdicts (signed work report v1, section 4-L1:
share conclusions must be same-direction under primary and backup queries to
enter the headlines). Direction rule frozen in
术语敏感性_备用检索式_冻结_2026-11-12.md: direction = relative change of the
5-year-period pool share, last period (2020-2024) vs first (1995-1999);
>= +5% up, <= -5% down, else flat. Agreement = identical direction labels.

Inputs: data_l1/l1_counts_by_year.csv (primary, frozen 2026-11-08) and
data_l1/l1_counts_backup_by_year.csv (backup, frozen queries 2026-11-12).
Output: data_l1/terminology_sensitivity.csv.
"""

import csv
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERIODS = [(1995, 1999), (2000, 2004), (2005, 2009),
           (2010, 2014), (2015, 2019), (2020, 2024)]
CANCERS = ["larynx_cancer", "oral_cancer", "nasopharynx_cancer",
           "other_pharynx_cancer", "thyroid_cancer"]


def load(path):
    yearly = defaultdict(dict)
    with open(path) as f:
        for r in csv.DictReader(f):
            yearly[r["area"]][int(r["year"])] = int(r["count"])
    return yearly


def period_counts(yearly):
    pc = {}
    for area, yd in yearly.items():
        pc[area] = [sum(yd[y] for y in range(a, b + 1)) for a, b in PERIODS]
    return pc


def direction(first_share, last_share):
    rel = (last_share - first_share) / first_share * 100
    if rel >= 5:
        return "up", rel
    if rel <= -5:
        return "down", rel
    return "flat", rel


def main():
    pri = period_counts(load(os.path.join(ROOT, "data_l1", "l1_counts_by_year.csv")))
    bak = period_counts(load(os.path.join(ROOT, "data_l1", "l1_counts_backup_by_year.csv")))
    areas = sorted(pri)
    assert areas == sorted(bak) and len(areas) == 14
    pri_pool = [sum(pri[a][i] for a in areas) for i in range(6)]
    bak_pool = [sum(bak[a][i] for a in areas) for i in range(6)]

    # anchors: primary pool endpoints are frozen L1 facts
    assert pri_pool[0] == 26544 and pri_pool[-1] == 128117, pri_pool

    rows = []
    for area in areas:
        ps = [pri[area][i] / pri_pool[i] * 100 for i in range(6)]
        bs = [bak[area][i] / bak_pool[i] * 100 for i in range(6)]
        pd_, prel = direction(ps[0], ps[-1])
        bd, brel = direction(bs[0], bs[-1])
        rows.append({
            "area": area,
            "primary_share_first": f"{ps[0]:.2f}", "primary_share_last": f"{ps[-1]:.2f}",
            "primary_rel_change_pct": f"{prel:.1f}", "primary_direction": pd_,
            "backup_share_first": f"{bs[0]:.2f}", "backup_share_last": f"{bs[-1]:.2f}",
            "backup_rel_change_pct": f"{brel:.1f}", "backup_direction": bd,
            "directions_agree": "yes" if pd_ == bd else "NO",
        })
    for label, members in (("five_cancers_combined", CANCERS),):
        ps = [sum(pri[a][i] for a in members) / pri_pool[i] * 100 for i in range(6)]
        bs = [sum(bak[a][i] for a in members) / bak_pool[i] * 100 for i in range(6)]
        pd_, prel = direction(ps[0], ps[-1])
        bd, brel = direction(bs[0], bs[-1])
        rows.append({
            "area": label,
            "primary_share_first": f"{ps[0]:.2f}", "primary_share_last": f"{ps[-1]:.2f}",
            "primary_rel_change_pct": f"{prel:.1f}", "primary_direction": pd_,
            "backup_share_first": f"{bs[0]:.2f}", "backup_share_last": f"{bs[-1]:.2f}",
            "backup_rel_change_pct": f"{brel:.1f}", "backup_direction": bd,
            "directions_agree": "yes" if pd_ == bd else "NO",
        })

    out = os.path.join(ROOT, "data_l1", "terminology_sensitivity.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"primary pool: {pri_pool[0]} -> {pri_pool[-1]}; backup pool: {bak_pool[0]} -> {bak_pool[-1]}")
    for r in rows:
        print(f"  {r['area']:<22} primary {r['primary_share_first']:>5}%->{r['primary_share_last']:>5}% "
              f"({r['primary_rel_change_pct']:>6}%, {r['primary_direction']:<4}) | "
              f"backup {r['backup_share_first']:>5}%->{r['backup_share_last']:>5}% "
              f"({r['backup_rel_change_pct']:>6}%, {r['backup_direction']:<4}) | agree: {r['directions_agree']}")
    n_no = sum(1 for r in rows if r["directions_agree"] == "NO")
    print(f"\ndisagreements: {n_no} of {len(rows)}")


if __name__ == "__main__":
    main()

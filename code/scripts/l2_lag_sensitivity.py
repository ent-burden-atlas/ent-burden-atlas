#!/usr/bin/env python3
"""
Lag-window sensitivity for ABR (signed work report v1, section 6: preset lag
windows 0/5/10 years as sensitivity; 'following/lagging' used as temporal
descriptors only, never as causal claims).

Operationalisation (fixed here before running): period-level lags. For
publication period index i, ABR_lag(k) = pub_share(i) / DALY_share(i-k),
k = 0, 1, 2 periods (= 0, 5, 10 years; burden leads, i.e. publications are
compared with the burden of k periods earlier — the 'research follows
burden' reading). Shares are the frozen within-pool shares from
data_l2/abr/abr_primary.csv; no new data are pulled.

Output: data_l2/abr/abr_lag_sensitivity.csv (long table) + printed verdict:
per area, the last-period (2020-2024) log2 ABR under the three lags and
whether its sign (over- vs under-attention) is unchanged.
"""

import csv
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABR_CSV = os.path.join(ROOT, "data_l2", "abr", "abr_primary.csv")
OUT = os.path.join(ROOT, "data_l2", "abr", "abr_lag_sensitivity.csv")
PERIODS = ["1995-1999", "2000-2004", "2005-2009",
           "2010-2014", "2015-2019", "2020-2024"]


def main():
    pub, bur = {}, {}
    areas = []
    with open(ABR_CSV) as f:
        for r in csv.DictReader(f):
            if r["area"] not in areas:
                areas.append(r["area"])
            pub[(r["area"], r["period"])] = float(r["pub_share_burden_pool"])
            bur[(r["area"], r["period"])] = float(r["burden_share_pool"])

    rows = []
    for area in areas:
        for i, p in enumerate(PERIODS):
            for k in (0, 1, 2):
                j = i - k
                if j < 0:
                    continue
                abr = pub[(area, p)] / bur[(area, PERIODS[j])]
                rows.append({
                    "area": area, "pub_period": p, "lag_years": k * 5,
                    "burden_period_used": PERIODS[j],
                    "abr_lag": f"{abr:.6f}", "log2_abr_lag": f"{math.log2(abr):.6f}",
                })
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"rows: {len(rows)} (7 areas x (6+5+4) lag cells = 105 expected)")
    assert len(rows) == 105
    print("\nLast-period (pub 2020-2024) log2 ABR by lag (burden leads):")
    last = {}
    for r in rows:
        if r["pub_period"] == "2020-2024":
            last.setdefault(r["area"], {})[r["lag_years"]] = float(r["log2_abr_lag"])
    for area in areas:
        v = last[area]
        signs = {x > 0 for x in v.values()}
        print(f"  {area:<22} lag0 {v[0]:+.3f}  lag5 {v[5]:+.3f}  lag10 {v[10]:+.3f}"
              f"  sign-stable: {len(signs) == 1}")


if __name__ == "__main__":
    main()

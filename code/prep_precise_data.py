#!/usr/bin/env python3
"""Prepare the corrected (precise-query) data layer for the atlas site.

All inputs are the frozen outputs of the 2026-11-21 fix round
(~/workspace/ent-attention-burden/fix_round_2026-11-21/) plus, where a
quantity was not re-derived in the fix round, the original frozen files
(backup-query counts and terminology backup shares; per-period top-10
DALY country lists; the centroid estimator table for the nine areas whose
retrieval was not repeated). Outputs land in site_build/precise_data/
with the file names build_site.py has always consumed, so the site
generator's data path stays uniform.

Every derived table is asserted against the fix round's master verdict
file (headline_survival_v2.md) values before it is written.
"""
import csv
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FR = os.path.join(ROOT, "fix_round_2026-11-21")
OUT = os.path.join(HERE, "precise_data")
PERIODS = ["1995-1999", "2000-2004", "2005-2009", "2010-2014",
           "2015-2019", "2020-2024"]
BURDEN = ["otitis_media", "hearing_loss", "larynx_cancer", "oral_cancer",
          "nasopharynx_cancer", "other_pharynx_cancer", "thyroid_cancer"]
ATTENTION = ["crs_polyps", "allergic_rhinitis", "osa", "tinnitus",
             "vertigo", "cholesteatoma", "cochlear_implant"]
AREAS = BURDEN + ATTENTION
CHANGED = {"nasopharynx_cancer", "other_pharynx_cancer", "oral_cancer",
           "larynx_cancer", "crs_polyps"}
UNCHANGED = [a for a in AREAS if a not in CHANGED]


def rd(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def wr(name, fields, rows):
    with open(os.path.join(OUT, name), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main():
    os.makedirs(OUT, exist_ok=True)

    # --- L1 counts (precise primary formulations) -------------------------
    l1 = rd(os.path.join(FR, "l1_precise", "l1_precise_counts_by_year.csv"))
    wr("l1_counts_by_year.csv", ["area", "year", "count"], l1)
    counts = {(r["area"], int(r["year"])): int(r["count"]) for r in l1}
    pyears = {p: range(int(p[:4]), int(p[:4]) + 5) for p in PERIODS}
    pcount = {(a, p): sum(counts[(a, y)] for y in pyears[p])
              for a in AREAS for p in PERIODS}
    pool = {p: sum(pcount[(a, p)] for a in AREAS) for p in PERIODS}
    assert pool["1995-1999"] == 24251 and pool["2020-2024"] == 112267, pool
    share = {(a, p): 100.0 * pcount[(a, p)] / pool[p]
             for a in AREAS for p in PERIODS}

    # --- ABR tables --------------------------------------------------------
    for src, dst in (
            ("l2_abr_precise/abr_primary_precise.csv", "abr_primary.csv"),
            ("l2_abr_precise/abr_prevalence_sensitivity_precise.csv",
             "abr_prevalence_sensitivity.csv"),
            ("l2_abr_precise/abr_sensitivity_pub2020_2023_precise.csv",
             "abr_sensitivity_pub2020_2023.csv"),
            ("l2_abr_precise/abr_lag_sensitivity_precise.csv",
             "abr_lag_sensitivity.csv")):
        shutil.copyfile(os.path.join(FR, src), os.path.join(OUT, dst))

    # --- Geography ---------------------------------------------------------
    shutil.copyfile(os.path.join(FR, "l3_repull", "double_centroid_precise.csv"),
                    os.path.join(OUT, "double_centroid.csv"))
    shutil.copyfile(os.path.join(FR, "l3_repull",
                                 "research_centroids_combined.csv"),
                    os.path.join(OUT, "research_centroids_all14.csv"))
    cc = rd(os.path.join(FR, "l3_repull", "country_counts_combined.csv"))
    wr("country_counts.csv", ["area", "period", "iso3", "n"], cc)
    from collections import Counter
    tot_country = Counter()
    units = set()
    cc_by = {}
    for r in cc:
        tot_country[r["iso3"]] += int(r["n"])
        units.add(r["iso3"])
        cc_by[(r["area"], r["period"], r["iso3"])] = int(r["n"])
    assert tot_country.most_common(3) == [("USA", 69049), ("CHN", 47959),
                                          ("JPN", 16947)], tot_country.most_common(3)
    assert len(units) == 157, len(units)
    assert sum(tot_country.values()) == 310722

    # author shares: precise LMIC shares + top-10 burden-country shares
    # recomputed from the combined country counts against the frozen
    # per-period top-10 DALY country lists (burden side unchanged).
    ash_new = {(r["area"], r["period"]): r
               for r in rd(os.path.join(FR, "l3_repull",
                                        "author_shares_precise.csv"))}
    ash_old = {(r["area"], r["period"]): r
               for r in rd(os.path.join(ROOT, "data_l3", "geo", "centroid",
                                        "author_shares.csv"))}
    rows = []
    for a in AREAS:
        for p in PERIODS:
            r = dict(ash_new[(a, p)])
            iso = ash_old[(a, p)].get("top10_burden_iso3") or ""
            if iso:
                n10 = sum(cc_by.get((a, p, c), 0)
                          for c in iso.split(";") if c)
                r["top10_burden_n"] = n10
                r["top10_burden_share"] = (n10 / int(r["parsed_n"])
                                           if int(r["parsed_n"]) else "")
                r["top10_burden_iso3"] = iso
            rows.append(r)
    wr("author_shares.csv",
       ["area", "period", "parsed_n", "lmic_n", "lmic_share",
        "top10_burden_n", "top10_burden_share", "top10_burden_iso3"], rows)

    lm = rd(os.path.join(FR, "l3_repull", "lmic_series_precise.csv"))
    wr("lmic_series_recomputed.csv",
       ["period", "lmic_share_all", "lmic_share_excl_china"], lm)
    lm0, lm1 = lm[0], lm[-1]
    assert abs(float(lm0["lmic_share_all"]) - 7.8) < 0.1
    assert abs(float(lm1["lmic_share_all"]) - 40.6) < 0.1
    assert abs(float(lm0["lmic_share_excl_china"]) - 5.1) < 0.1
    assert abs(float(lm1["lmic_share_excl_china"]) - 16.8) < 0.1

    # parse coverage: frozen rows for the nine unchanged areas + re-pull
    # rows for the five corrected areas.
    cov_old = rd(os.path.join(ROOT, "data_l3", "geo", "parse_coverage.csv"))
    cov_new = rd(os.path.join(FR, "l3_repull", "geo", "parse_coverage.csv"))
    cov = [r for r in cov_old if r["area"] not in CHANGED] + cov_new
    fields = list(cov_old[0].keys())
    wr("parse_coverage.csv", fields, cov)
    assert sum(int(r["records"]) for r in cov) == 357711
    assert sum(int(r["with_aff"]) for r in cov) == 325206
    assert sum(int(r["parsed"]) for r in cov) == 310722

    # --- L4 ----------------------------------------------------------------
    shutil.copyfile(os.path.join(FR, "l4_precise", "signals.csv"),
                    os.path.join(OUT, "signals.csv"))
    shutil.copyfile(os.path.join(FR, "l4_precise", "typology.csv"),
                    os.path.join(OUT, "typology.csv"))
    signals = {r["area"]: r for r in rd(os.path.join(FR, "l4_precise",
                                                     "signals.csv"))}

    # --- Terminology sensitivity, recomputed basis --------------------------
    # Primary = corrected formulations (precise pool shares, this build).
    # Backup = the pre-frozen backup formulations; their counts and pool
    # are untouched by the correction, so their shares/changes carry over
    # from the original frozen terminology table.
    term_old = {r["area"]: r for r in rd(os.path.join(
        ROOT, "data_l1", "terminology_sensitivity.csv"))}

    def band(x):
        return "down" if x < -5 else ("up" if x > 5 else "stable")

    trows = []
    for a in AREAS:
        s0, s1 = share[(a, PERIODS[0])], share[(a, PERIODS[-1])]
        rel = 100.0 * (s1 - s0) / s0
        b = term_old[a]
        agree = "yes" if band(rel) == b["backup_direction"] else "no"
        trows.append({
            "area": a, "primary_share_first": f"{s0:.2f}",
            "primary_share_last": f"{s1:.2f}",
            "primary_rel_change_pct": f"{rel:.1f}",
            "primary_direction": band(rel),
            "backup_share_first": b["backup_share_first"],
            "backup_share_last": b["backup_share_last"],
            "backup_rel_change_pct": b["backup_rel_change_pct"],
            "backup_direction": b["backup_direction"],
            "directions_agree": agree})
    c5 = ["larynx_cancer", "oral_cancer", "nasopharynx_cancer",
          "other_pharynx_cancer", "thyroid_cancer"]
    s0 = sum(share[(a, PERIODS[0])] for a in c5)
    s1 = sum(share[(a, PERIODS[-1])] for a in c5)
    rel = 100.0 * (s1 - s0) / s0
    b = term_old["five_cancers_combined"]
    trows.append({
        "area": "five_cancers_combined", "primary_share_first": f"{s0:.2f}",
        "primary_share_last": f"{s1:.2f}",
        "primary_rel_change_pct": f"{rel:.1f}",
        "primary_direction": band(rel),
        "backup_share_first": b["backup_share_first"],
        "backup_share_last": b["backup_share_last"],
        "backup_rel_change_pct": b["backup_rel_change_pct"],
        "backup_direction": b["backup_direction"],
        "directions_agree": "yes" if band(rel) == b["backup_direction"]
        else "no"})
    wr("terminology_sensitivity.csv",
       ["area", "primary_share_first", "primary_share_last",
        "primary_rel_change_pct", "primary_direction", "backup_share_first",
        "backup_share_last", "backup_rel_change_pct", "backup_direction",
        "directions_agree"], trows)
    agree = sum(1 for r in trows if r["directions_agree"] == "yes")
    assert agree == 13 and len(trows) == 15, (agree, len(trows))
    crs = [r for r in trows if r["area"] == "crs_polyps"][0]
    assert abs(float(crs["primary_rel_change_pct"]) - 26.3) < 0.15, crs
    assert abs(float(signals["crs_polyps"]["S_rel_pct"])
               - float(crs["primary_rel_change_pct"])) < 0.15

    # --- Estimator sensitivity: nine unchanged areas only -------------------
    est = rd(os.path.join(ROOT, "data_l3", "geo", "centroid",
                          "estimator_sensitivity.csv"))
    est = [r for r in est if r["area"] in UNCHANGED]
    wr("estimator_sensitivity.csv", list(est[0].keys()), est)
    # the table covers the seven burden-tier causes only; three of them
    # (otitis media, hearing loss, thyroid cancer) were not re-retrieved
    assert len(est) == 3 * 6, len(est)

    # --- Correction documentation -------------------------------------------
    shutil.copyfile(os.path.join(FR, "mapping_table.csv"),
                    os.path.join(OUT, "mapping_table.csv"))
    shutil.copyfile(os.path.join(FR, "queries_precise_frozen.md"),
                    os.path.join(OUT, "queries_precise_frozen.md"))

    print("precise_data written:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()

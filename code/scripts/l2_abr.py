#!/usr/bin/env python3
"""
L2 ABR + L3 double-centroid production script (ENT attention-burden census).

Design sources (frozen):
- Work report v1 (user-signed 2026-11-08) section 4: L2 ABR, L3 geographic
  double centroid, auxiliary author shares.
- Protocol amendment v1.1 (user-approved 2026-11-10): burden source GBD 2023,
  burden years 1995-2023, periods unchanged (1995-99 ... 2020-24) but the last
  period's BURDEN side uses 2020-23 (4 years). ABR primary = frozen L1
  publication shares (last period 2020-24) / same-labelled DALY shares
  (burden 2020-23 for the last period; mismatch disclosed). ABR sensitivity =
  last-period publication counts restricted to 2020-23.
- Prevalence-share ABR is the second sensitivity (work report section 4-L2).

Definitions:
- ABR pool = the 7 burden-tier areas only. pub_share and daly_share are both
  within-pool composition shares ("same pool" per spec L2_GBD section 3).
- DALY/prevalence shares use the GBD "Global" location row, Metric=Number.
- Double centroid: spherical (3-D unit-vector) weighted mean of country-centre
  lat/lon. Burden weights = country DALY (Number) summed over the period's
  burden years, Global row excluded. Research weights = parsed first-author
  records per ISO3 from frozen data_l3/geo/country_counts.csv (no imputation;
  unparsed/missing records never enter the centroid, coverage reported).
- Country centres: mledoze/countries snapshot latlng (see ref/ PROVENANCE in
  the output FREEZE file). GBD location_name -> ISO3 mapping is generated from
  the same snapshot's common/official names plus the frozen MANUAL_ISO_PATCHES
  below, asserted complete and written out as an auditable CSV.
- LMIC share: World Bank income classification snapshot (accessed
  2026-11-12, applied FIXED to all periods; implementation decision, disclosed
  in the FREEZE file). LMIC = LIC+LMC+UMC (incomeLevel id != HIC). Records
  from economies with no classification in the snapshot (or the TWN manual
  patch, see code) are handled explicitly and listed in the run log.
- Top-10 burden-country author share: per burden-tier area x period, the 10
  locations with the largest period DALY; share of that area's parsed
  first-author records coming from those 10 countries.

Outputs (see FREEZE file written alongside):
  data_l2/abr/abr_primary.csv
  data_l2/abr/abr_sensitivity_pub2020_2023.csv
  data_l2/abr/abr_prevalence_sensitivity.csv
  data_l3/geo/centroid/double_centroid.csv
  data_l3/geo/centroid/research_centroids_all14.csv
  data_l3/geo/centroid/author_shares.csv
  data_l3/geo/ref/country_reference.csv
  data_l3/geo/ref/gbd_location_iso_map.csv
"""

import csv
import json
import math
import os
import sys
import unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L1_CSV = os.path.join(ROOT, "data_l1", "l1_counts_by_year.csv")
L2_RAW = os.path.join(ROOT, "data_l2", "raw")
GEO_DIR = os.path.join(ROOT, "data_l3", "geo")
COUNTRY_COUNTS = os.path.join(GEO_DIR, "country_counts.csv")
PARSE_COVERAGE = os.path.join(GEO_DIR, "parse_coverage.csv")
REF_DIR = os.path.join(GEO_DIR, "ref")
MLEDOZE_JSON = os.path.join(REF_DIR, "countries_mledoze.json")
WB_JSON = os.path.join(REF_DIR, "worldbank_country_income.json")
ABR_DIR = os.path.join(ROOT, "data_l2", "abr")
CENT_DIR = os.path.join(GEO_DIR, "centroid")

BURDEN_AREAS = [
    "otitis_media",
    "hearing_loss",
    "larynx_cancer",
    "oral_cancer",
    "nasopharynx_cancer",
    "other_pharynx_cancer",
    "thyroid_cancer",
]
CAUSE_NAMES = {
    "otitis_media": "Otitis media",
    "hearing_loss": "Age-related and other hearing loss",
    "larynx_cancer": "Larynx cancer",
    "oral_cancer": "Lip and oral cavity cancer",
    "nasopharynx_cancer": "Nasopharynx cancer",
    "other_pharynx_cancer": "Other pharynx cancer",
    "thyroid_cancer": "Thyroid cancer",
}
# period label, pub years, burden years
PERIODS = [
    ("1995-1999", range(1995, 2000), range(1995, 2000)),
    ("2000-2004", range(2000, 2005), range(2000, 2005)),
    ("2005-2009", range(2005, 2010), range(2005, 2010)),
    ("2010-2014", range(2010, 2015), range(2010, 2015)),
    ("2015-2019", range(2015, 2020), range(2015, 2020)),
    ("2020-2024", range(2020, 2025), range(2020, 2024)),  # burden side 2020-23 (amendment v1.1)
]

# GBD location names whose ISO3 cannot be matched unambiguously from the
# mledoze common/official names. Frozen; every entry verified by hand against
# the GBD location list printed 2026-11-12.
MANUAL_ISO_PATCHES = {
    "Bolivia (Plurinational State of)": "BOL",
    "Venezuela (Bolivarian Republic of)": "VEN",
    "Iran (Islamic Republic of)": "IRN",
    "Micronesia (Federated States of)": "FSM",
    "Viet Nam": "VNM",
    "Brunei Darussalam": "BRN",
    "Türkiye": "TUR",
    "Taiwan": "TWN",
    "Cabo Verde": "CPV",  # reference snapshot uses common name "Cape Verde"
}
# World Bank API v2 country list (snapshot 2026-11-12) contains no Taiwan
# entry; Taiwan is a high-income economy in the World Bank classification.
# Flagged in country_reference.csv as income_source=manual_patch.
MANUAL_INCOME_PATCHES = {"TWN": ("HIC", "High income")}

EARTH_R_KM = 6371.0088


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join("".join(c if c.isalnum() else " " for c in s.lower()).split())


def spherical_centroid(weighted_latlon):
    """weighted_latlon: list of (lat_deg, lon_deg, weight). Returns (lat, lon)."""
    x = y = z = wsum = 0.0
    for lat, lon, w in weighted_latlon:
        la, lo = math.radians(lat), math.radians(lon)
        x += w * math.cos(la) * math.cos(lo)
        y += w * math.cos(la) * math.sin(lo)
        z += w * math.sin(la)
        wsum += w
    assert wsum > 0
    x, y, z = x / wsum, y / wsum, z / wsum
    lon = math.degrees(math.atan2(y, x))
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    return lat, lon


def haversine_km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * EARTH_R_KM * math.asin(min(1.0, math.sqrt(h)))


def main():
    log = []
    os.makedirs(ABR_DIR, exist_ok=True)
    os.makedirs(CENT_DIR, exist_ok=True)

    # ---------- reference tables ----------
    mledoze = json.load(open(MLEDOZE_JSON))
    centre = {}      # iso3 -> (lat, lon)
    name2iso = {}    # normalised name -> iso3
    for c in mledoze:
        iso = c["cca3"]
        if c.get("latlng") and len(c["latlng"]) == 2:
            centre[iso] = (c["latlng"][0], c["latlng"][1])
        for nm in {c["name"]["common"], c["name"]["official"]} | set(c.get("altSpellings", [])):
            name2iso.setdefault(norm(nm), iso)

    wb = json.load(open(WB_JSON))
    income = {}  # iso3 -> (income_id, income_label)
    for e in wb[1]:
        if e["region"]["id"] == "NA":  # aggregates, not economies
            continue
        income[e["id"]] = (e["incomeLevel"]["id"], e["incomeLevel"]["value"])

    # ---------- L1 publication counts ----------
    l1 = defaultdict(dict)  # area -> year -> count
    with open(L1_CSV) as f:
        for r in csv.DictReader(f):
            l1[r["area"]][int(r["year"])] = int(r["count"])
    all_areas = sorted(l1)
    assert set(BURDEN_AREAS) <= set(all_areas), "burden areas missing from L1"

    def pub_count(area, years):
        return sum(l1[area][y] for y in years)

    # ---------- GBD files ----------
    # gbd[measure][area] = {('global', year): val, ('loc', location_name, year): val}
    gbd = {"dalys": {}, "prevalence": {}}
    gbd_locations = None
    for measure in ("dalys", "prevalence"):
        for area in BURDEN_AREAS:
            path = os.path.join(L2_RAW, f"gbd2023_{area}_{measure}_raw.csv")
            glob, locs, loc_names = {}, defaultdict(float), set()
            cause_seen = set()
            with open(path) as f:
                for r in csv.DictReader(f):
                    if r["metric_name"] != "Number":
                        continue
                    cause_seen.add((int(r["cause_id"]), r["cause_name"]))
                    year, val = int(r["year"]), float(r["val"])
                    loc_names.add(r["location_name"])
                    if r["location_name"] == "Global":
                        glob[year] = val
                    else:
                        locs[(r["location_name"], year)] += val
            assert len(cause_seen) == 1 and list(cause_seen)[0][1] == CAUSE_NAMES[area], \
                f"{path}: cause mismatch {cause_seen}"
            assert set(glob) == set(range(1995, 2024)), f"{path}: global years incomplete"
            if gbd_locations is None:
                gbd_locations = loc_names
            else:
                assert loc_names == gbd_locations, f"{path}: location set differs"
            gbd[measure][area] = (glob, locs)
    country_locations = sorted(gbd_locations - {"Global"})
    assert len(country_locations) == 204, f"expected 204 countries, got {len(country_locations)}"
    log.append(f"GBD locations: 204 countries + Global; all 14 files cause-asserted OK")

    # ---------- GBD location -> ISO3 map ----------
    loc2iso, patch_used, unmapped = {}, set(), []
    for name in country_locations:
        if name in MANUAL_ISO_PATCHES:
            loc2iso[name] = MANUAL_ISO_PATCHES[name]
            patch_used.add(name)
        elif norm(name) in name2iso:
            loc2iso[name] = name2iso[norm(name)]
        else:
            unmapped.append(name)
    assert not unmapped, f"unmapped GBD locations: {unmapped}"
    assert len(set(loc2iso.values())) == 204, "ISO3 collision in GBD location map"
    missing_centre_gbd = [n for n, i in loc2iso.items() if i not in centre]
    assert not missing_centre_gbd, f"GBD locations without centre: {missing_centre_gbd}"
    log.append(f"GBD->ISO map: 204/204 mapped ({len(patch_used)} via manual patches: "
               f"{sorted(patch_used)})")

    with open(os.path.join(REF_DIR, "gbd_location_iso_map.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gbd_location_name", "iso3", "mapping_source"])
        for name in country_locations:
            w.writerow([name, loc2iso[name],
                        "manual_patch" if name in MANUAL_ISO_PATCHES else "mledoze_name_match"])

    # ---------- L3 country counts + coverage ----------
    cc = defaultdict(dict)  # (area, period) -> iso3 -> n
    with open(COUNTRY_COUNTS) as f:
        for r in csv.DictReader(f):
            cc[(r["area"], r["period"])][r["iso3"]] = int(r["n"])
    coverage = {}  # (area, period) -> dict(records, parsed)
    with open(PARSE_COVERAGE) as f:
        for r in csv.DictReader(f):
            coverage[(r["area"], r["period"])] = {
                "records": int(r["records"]), "parsed": int(r["parsed"])}
    l3_isos = sorted({i for d in cc.values() for i in d})
    missing_centre_l3 = [i for i in l3_isos if i not in centre]
    log.append(f"L3 ISO units: {len(l3_isos)}; without centre in reference: {missing_centre_l3}")

    # country reference table (union of GBD + L3 ISO units)
    ref_isos = sorted(set(loc2iso.values()) | set(l3_isos))
    with open(os.path.join(REF_DIR, "country_reference.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["iso3", "centre_lat", "centre_lon", "wb_income_id", "wb_income_label",
                    "income_source", "is_lmic"])
        for iso in ref_isos:
            lat, lon = centre.get(iso, ("", ""))
            if iso in MANUAL_INCOME_PATCHES:
                iid, ilab, isrc = MANUAL_INCOME_PATCHES[iso][0], MANUAL_INCOME_PATCHES[iso][1], "manual_patch"
            elif iso in income:
                iid, ilab, isrc = income[iso][0], income[iso][1], "worldbank_api_snapshot_2026-11-12"
            else:
                iid, ilab, isrc = "", "", "not_in_snapshot"
            is_lmic = "" if not iid else ("0" if iid == "HIC" else "1")
            w.writerow([iso, lat, lon, iid, ilab, isrc, is_lmic])
    no_income = [i for i in ref_isos if i not in income and i not in MANUAL_INCOME_PATCHES]
    log.append(f"Reference ISO units: {len(ref_isos)}; no WB income in snapshot: {no_income}")

    # ---------- ABR tables ----------
    def abr_table(pub_years_by_period, burden_measure, out_path, variant_label):
        rows = []
        for plabel, _, burden_years in PERIODS:
            pub_years = pub_years_by_period[plabel]
            pubs = {a: pub_count(a, pub_years) for a in BURDEN_AREAS}
            burs = {a: sum(gbd[burden_measure][a][0][y] for y in burden_years)
                    for a in BURDEN_AREAS}
            ptot, btot = sum(pubs.values()), sum(burs.values())
            for a in BURDEN_AREAS:
                pshare, bshare = pubs[a] / ptot, burs[a] / btot
                rows.append({
                    "area": a, "period": plabel, "variant": variant_label,
                    "pub_years": f"{min(pub_years)}-{max(pub_years)}",
                    "burden_years": f"{min(burden_years)}-{max(burden_years)}",
                    "pub_count": pubs[a], "pub_pool_total": ptot,
                    "pub_share_burden_pool": f"{pshare:.6f}",
                    "burden_global": f"{burs[a]:.3f}", "burden_pool_total": f"{btot:.3f}",
                    "burden_share_pool": f"{bshare:.6f}",
                    "abr": f"{pshare / bshare:.6f}",
                    "log2_abr": f"{math.log2(pshare / bshare):.6f}",
                })
            s = sum(float(r["burden_share_pool"]) for r in rows if r["period"] == plabel)
            assert abs(s - 1.0) < 1e-5, f"{variant_label} {plabel}: burden shares sum {s}"
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return rows

    primary = abr_table({p[0]: p[1] for p in PERIODS}, "dalys",
                        os.path.join(ABR_DIR, "abr_primary.csv"), "primary_daly")
    sens_years = {p[0]: p[1] for p in PERIODS}
    sens_years["2020-2024"] = range(2020, 2024)  # pub side restricted to 2020-23
    abr_table(sens_years, "dalys",
              os.path.join(ABR_DIR, "abr_sensitivity_pub2020_2023.csv"),
              "sensitivity_pub_2020_2023")
    abr_table({p[0]: p[1] for p in PERIODS}, "prevalence",
              os.path.join(ABR_DIR, "abr_prevalence_sensitivity.csv"),
              "sensitivity_prevalence")
    log.append("ABR tables: 3 variants x 7 areas x 6 periods = 126 rows each; "
               "burden shares sum to 1 per period (asserted)")

    # ---------- centroids + author shares ----------
    double_rows, research_rows, share_rows = [], [], []
    for area in all_areas:
        for plabel, _, burden_years in PERIODS:
            by_iso = cc.get((area, plabel), {})
            parsed_total = sum(by_iso.values())
            cov = coverage[(area, plabel)]
            assert parsed_total == cov["parsed"], \
                f"{area} {plabel}: country_counts sum {parsed_total} != coverage parsed {cov['parsed']}"
            wpts = [(centre[i][0], centre[i][1], n) for i, n in by_iso.items() if i in centre]
            wsum = sum(w for _, _, w in wpts)
            rlat, rlon = spherical_centroid(wpts)
            research_rows.append({
                "area": area, "period": plabel,
                "research_centroid_lat": f"{rlat:.5f}", "research_centroid_lon": f"{rlon:.5f}",
                "parsed_n": parsed_total, "records_n": cov["records"],
                "centroid_weight_n": wsum,
                "centroid_coverage_of_parsed": f"{wsum / parsed_total:.6f}",
            })
            # LMIC author share (unclassified economies: not counted as LMIC)
            lmic_n = sum(n for i, n in by_iso.items()
                         if income.get(i, MANUAL_INCOME_PATCHES.get(i, ("", "")))[0]
                         not in ("", "HIC"))
            share_row = {
                "area": area, "period": plabel, "parsed_n": parsed_total,
                "lmic_n": lmic_n, "lmic_share": f"{lmic_n / parsed_total:.6f}",
                "top10_burden_n": "", "top10_burden_share": "", "top10_burden_iso3": "",
            }
            if area in BURDEN_AREAS:
                locs = gbd["dalys"][area][1]
                per_loc = defaultdict(float)
                for (lname, yr), v in locs.items():
                    if yr in burden_years:
                        per_loc[lname] += v
                country_sum = sum(per_loc.values())
                glob_sum = sum(gbd["dalys"][area][0][y] for y in burden_years)
                top10 = sorted(per_loc, key=per_loc.get, reverse=True)[:10]
                top10_iso = [loc2iso[n] for n in top10]
                t10n = sum(by_iso.get(i, 0) for i in top10_iso)
                share_row.update({
                    "top10_burden_n": t10n,
                    "top10_burden_share": f"{t10n / parsed_total:.6f}",
                    "top10_burden_iso3": ";".join(top10_iso),
                })
                bw = [(centre[loc2iso[n]][0], centre[loc2iso[n]][1], v)
                      for n, v in per_loc.items()]
                blat, blon = spherical_centroid(bw)
                double_rows.append({
                    "area": area, "period": plabel,
                    "burden_years": f"{min(burden_years)}-{max(burden_years)}",
                    "burden_centroid_lat": f"{blat:.5f}", "burden_centroid_lon": f"{blon:.5f}",
                    "burden_country_daly_sum": f"{country_sum:.3f}",
                    "burden_global_daly": f"{glob_sum:.3f}",
                    "country_sum_over_global": f"{country_sum / glob_sum:.6f}",
                    "research_centroid_lat": f"{rlat:.5f}", "research_centroid_lon": f"{rlon:.5f}",
                    "research_parsed_n": parsed_total,
                    "distance_km": f"{haversine_km(blat, blon, rlat, rlon):.1f}",
                })
            share_rows.append(share_row)

    for rows, path in (
        (double_rows, os.path.join(CENT_DIR, "double_centroid.csv")),
        (research_rows, os.path.join(CENT_DIR, "research_centroids_all14.csv")),
        (share_rows, os.path.join(CENT_DIR, "author_shares.csv")),
    ):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    log.append(f"double_centroid rows: {len(double_rows)} (7 areas x 6 periods)")
    log.append(f"research_centroids_all14 rows: {len(research_rows)}; author_shares rows: {len(share_rows)}")

    print("\n".join(log))
    print("\nABR primary (log2 ABR by area x period):")
    hdr = ["area"] + [p[0] for p in PERIODS]
    print("\t".join(hdr))
    for a in BURDEN_AREAS:
        vals = [r["log2_abr"] for r in primary if r["area"] == a]
        print(a, "\t".join(vals), sep="\t")
    print("\nDouble-centroid distance km (area: first -> last period):")
    for a in BURDEN_AREAS:
        ds = [r["distance_km"] for r in double_rows if r["area"] == a]
        print(f"  {a}: {ds[0]} -> {ds[-1]}  all={ds}")


if __name__ == "__main__":
    main()

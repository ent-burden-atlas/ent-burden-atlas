#!/usr/bin/env python3
"""Centroid layer v2 — arithmetic mean-centre re-freeze (user rulings 2026-11-12).

Primary estimator (both sides): the spatial-statistics mean centre — weighted
arithmetic mean of country-centre latitudes and circular (unit-vector) mean of
longitudes; distance by haversine, R = 6371.0088 km. Chosen after two rejected
alternatives (see data_l3/geo/centroid/ESTIMATOR_诊断_2026-11-12.md): the v1
chordal mean puts ring-shaped research distributions in the Arctic (82N), and
the spherical geometric median degenerates to distance 0 for nasopharyngeal
cancer (both sides' medians snap to China's centre). The median and chordal
calibres are retained in estimator_sensitivity.csv; all three agree on the
direction of every distance change.

Inputs (frozen, read-only):
  data_l3/geo/country_counts.csv           research weights (14 areas x 6 periods)
  data_l3/geo/ref/country_reference.csv    country centres (mledoze snapshot)
  data_l3/geo/ref/gbd_location_iso_map.csv GBD location -> ISO3
  data_l2/raw/gbd2023_<area>_dalys_raw.csv burden weights (DALY Number, period sums;
                                           last period burden years 2020-2023, Amdt v1.1)

Outputs:
  data_l3/geo/centroid/archive_chordal_v1/{double_centroid,research_centroids_all14}.csv
  data_l3/geo/centroid/double_centroid.csv            (v2, arith; same schema as v1)
  data_l3/geo/centroid/research_centroids_all14.csv   (v2, arith; same schema as v1)
  data_l3/geo/centroid/estimator_sensitivity.csv      (42 cells x 3 estimators)
  data_l3/geo/centroid/FREEZE_v2.md                    (written by hand after review)
author_shares.csv is count-based and estimator-independent: left untouched.
"""
import csv, math, os, shutil, sys
from collections import defaultdict

ROOT = os.path.expanduser("~/workspace/ent-attention-burden")
CENT = f"{ROOT}/data_l3/geo/centroid"
PERIODS = ["1995-1999", "2000-2004", "2005-2009", "2010-2014", "2015-2019", "2020-2024"]
BURDEN_YEARS = {p: range(int(p[:4]), int(p[:4]) + 5) for p in PERIODS}
BURDEN_YEARS["2020-2024"] = range(2020, 2024)  # amendment v1.1: burden 2020-2023
BURDEN = ["otitis_media", "hearing_loss", "larynx_cancer", "oral_cancer",
          "nasopharynx_cancer", "other_pharynx_cancer", "thyroid_cancer"]
EARTH_R = 6371.0088

ref = {r['iso3']: (float(r['centre_lat']), float(r['centre_lon']))
       for r in csv.DictReader(open(f"{ROOT}/data_l3/geo/ref/country_reference.csv")) if r['centre_lat']}
loc2iso = {r['gbd_location_name']: r['iso3']
           for r in csv.DictReader(open(f"{ROOT}/data_l3/geo/ref/gbd_location_iso_map.csv"))}

def chordal(pts):
    x = y = z = 0.0
    for la, lo, w in pts:
        a, o = math.radians(la), math.radians(lo)
        x += w * math.cos(a) * math.cos(o); y += w * math.cos(a) * math.sin(o); z += w * math.sin(a)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))

def geo_median(pts, tol=1e-6, max_iter=5000):
    # Convergence: tangent-plane step < 1e-6 rad (~6 m on the surface) OR the
    # relative per-iteration improvement of the objective (total weighted
    # geodesic distance) < 1e-10. Both are far below the resolution of
    # country-centre data. The step criterion alone never trips when the median
    # coincides with a heavy data point (Weiszfeld then converges sublinearly,
    # step ~ 1/it), hence the objective criterion.
    la0, lo0 = chordal(pts)
    la, lo = math.radians(la0), math.radians(lo0)
    P = [(math.radians(a), math.radians(o), w) for a, o, w in pts]
    prev_obj = None
    for it in range(max_iter):
        num1 = num2 = den = obj = 0.0
        for a, o, w in P:
            dlon = o - lo
            cosc = max(-1.0, min(1.0, math.sin(la) * math.sin(a) + math.cos(la) * math.cos(a) * math.cos(dlon)))
            dist = math.acos(cosc)
            obj += w * dist
            if dist < 1e-9:
                continue
            sd = max(1e-12, math.sin(dist))
            x = math.cos(a) * math.sin(dlon) / sd * dist
            y = (math.cos(la) * math.sin(a) - math.sin(la) * math.cos(a) * math.cos(dlon)) / sd * dist
            wt = w / dist
            num1 += wt * x; num2 += wt * y; den += wt
        dx, dy = num1 / den, num2 / den
        step = math.hypot(dx, dy)
        if step < tol or (prev_obj is not None and abs(prev_obj - obj) <= 1e-10 * obj):
            return math.degrees(la), math.degrees(lo), it + 1, step
        prev_obj = obj
        ca, sa, cl, sl = math.cos(la), math.sin(la), math.cos(lo), math.sin(lo)
        px, py, pz = ca * cl, ca * sl, sa
        ex, ey, ez = -sl, cl, 0.0
        nx, ny, nz = -sa * cl, -sa * sl, ca
        ux, uy, uz = (ex * dx + nx * dy) / step, (ey * dx + ny * dy) / step, (ez * dx + nz * dy) / step
        cs, sn = math.cos(step), math.sin(step)
        qx, qy, qz = px * cs + ux * sn, py * cs + uy * sn, pz * cs + uz * sn
        la = math.asin(max(-1.0, min(1.0, qz))); lo = math.atan2(qy, qx)
    raise RuntimeError("geometric median did not converge")

def arith(pts):
    tw = sum(w for _, _, w in pts)
    lat = sum(la * w for la, _, w in pts) / tw
    sx = sum(w * math.cos(math.radians(lo)) for _, lo, w in pts)
    sy = sum(w * math.sin(math.radians(lo)) for _, lo, w in pts)
    return lat, math.degrees(math.atan2(sy, sx))

def hav(lat1, lon1, lat2, lon2):
    a, b, c, d = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(h)))

# ---------- weights ----------
res_w = defaultdict(list)          # (area, period) -> [(lat, lon, n)]
res_meta = {}                      # (area, period) -> (parsed_n, records_n)
for r in csv.DictReader(open(f"{ROOT}/data_l3/geo/country_counts.csv")):
    if r['iso3'] in ref:
        res_w[(r['area'], r['period'])].append((ref[r['iso3']][0], ref[r['iso3']][1], int(r['n'])))

v1_res = {(r['area'], r['period']): r for r in csv.DictReader(open(f"{CENT}/research_centroids_all14.csv"))}
v1_dc = {(r['area'], r['period']): r for r in csv.DictReader(open(f"{CENT}/double_centroid.csv"))}
for k, row in v1_res.items():
    res_meta[k] = (int(row['parsed_n']), int(row['records_n']))
    assert sum(w for _, _, w in res_w[k]) == int(row['centroid_weight_n']), f"weight mismatch {k}"

bur_w = {}                          # (area, period) -> [(lat, lon, daly)]
bur_global = {}                     # (area, period) -> global DALY sum (country rows + Global row check)
for area in BURDEN:
    per = defaultdict(lambda: defaultdict(float))
    glob = defaultdict(float)
    with open(f"{ROOT}/data_l2/raw/gbd2023_{area}_dalys_raw.csv") as f:
        for r in csv.DictReader(f):
            if r['metric_name'] != 'Number':
                continue
            y = int(r['year'])
            for p, yrs in BURDEN_YEARS.items():
                if y in yrs:
                    if r['location_name'] == 'Global':
                        glob[p] += float(r['val'])
                    else:
                        iso = loc2iso.get(r['location_name'])
                        if iso and iso in ref:
                            per[p][iso] += float(r['val'])
    for p in PERIODS:
        bur_w[(area, p)] = [(ref[i][0], ref[i][1], w) for i, w in per[p].items()]
        bur_global[(area, p)] = glob[p]

# ---------- compute ----------
med_res = {k: arith(pts) for k, pts in res_w.items()}
med_bur = {k: arith(pts) for k, pts in bur_w.items()}

# spot-checks against the independent diagnostic run (2026-11-12)
assert abs(med_res[('nasopharynx_cancer', '1995-1999')][0] - 34.8) < 0.15 and abs(med_res[('nasopharynx_cancer', '1995-1999')][1] - 43.0) < 0.15
assert abs(med_res[('nasopharynx_cancer', '2020-2024')][0] - 33.0) < 0.15 and abs(med_res[('nasopharynx_cancer', '2020-2024')][1] - 63.8) < 0.15
assert abs(med_bur[('otitis_media', '1995-1999')][0] - 22.4) < 0.15 and abs(med_bur[('otitis_media', '1995-1999')][1] - 70.5) < 0.15
# Pathology guards for the arithmetic calibre: no polar centroids, no
# degenerate (near-zero) distances, and every distance falls first -> last.
for k, (la, lo) in list(med_res.items()) + list(med_bur.items()):
    assert abs(la) <= 50, f"centroid latitude out of range at {k}: {la}"
for area in BURDEN:
    ds = [hav(*med_bur[(area, p)], *med_res[(area, p)]) for p in PERIODS]
    assert min(ds) > 500, f"degenerate distance for {area}: {min(ds):.0f}"
    assert ds[-1] < ds[0], f"distance did not fall for {area}"

# ---------- archive v1, write v2 ----------
os.makedirs(f"{CENT}/archive_chordal_v1", exist_ok=True)
for fn in ("double_centroid.csv", "research_centroids_all14.csv"):
    if not os.path.exists(f"{CENT}/archive_chordal_v1/{fn}"):
        shutil.copy2(f"{CENT}/{fn}", f"{CENT}/archive_chordal_v1/{fn}")

areas14 = sorted({a for a, _ in res_w})
with open(f"{CENT}/research_centroids_all14.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["area", "period", "research_centroid_lat", "research_centroid_lon",
                "parsed_n", "records_n", "centroid_weight_n", "centroid_coverage_of_parsed"])
    for area in areas14:
        for p in PERIODS:
            la, lo = med_res[(area, p)]
            pn, rn = res_meta[(area, p)]
            wn = sum(x[2] for x in res_w[(area, p)])
            w.writerow([area, p, f"{la:.5f}", f"{lo:.5f}", pn, rn, wn, f"{wn / pn:.6f}"])

sens_rows = []
with open(f"{CENT}/double_centroid.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["area", "period", "burden_years", "burden_centroid_lat", "burden_centroid_lon",
                "burden_country_daly_sum", "burden_global_daly", "country_sum_over_global",
                "research_centroid_lat", "research_centroid_lon", "research_parsed_n", "distance_km"])
    for area in BURDEN:
        for p in PERIODS:
            bla, blo = med_bur[(area, p)]
            rla, rlo = med_res[(area, p)]
            csum = sum(x[2] for x in bur_w[(area, p)])
            g = bur_global[(area, p)]
            dist = hav(bla, blo, rla, rlo)
            yrs = "2020-2023" if p == "2020-2024" else p
            w.writerow([area, p, yrs, f"{bla:.5f}", f"{blo:.5f}", f"{csum:.3f}", f"{g:.3f}",
                        f"{csum / g:.6f}", f"{rla:.5f}", f"{rlo:.5f}", res_meta[(area, p)][0], f"{dist:.1f}"])
            # sensitivity row: chordal / geometric-median / arithmetic (primary)
            cb = chordal(bur_w[(area, p)]); cr = chordal(res_w[(area, p)])
            mb = geo_median(bur_w[(area, p)])[:2]; mr = geo_median(res_w[(area, p)])[:2]
            sens_rows.append([area, p,
                              f"{hav(*cb, *cr):.1f}", f"{cr[0]:.5f}", f"{cr[1]:.5f}", f"{cb[0]:.5f}", f"{cb[1]:.5f}",
                              f"{hav(*mb, *mr):.1f}", f"{mr[0]:.5f}", f"{mr[1]:.5f}", f"{mb[0]:.5f}", f"{mb[1]:.5f}",
                              f"{dist:.1f}", f"{rla:.5f}", f"{rlo:.5f}", f"{bla:.5f}", f"{blo:.5f}"])

with open(f"{CENT}/estimator_sensitivity.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["area", "period", "dist_chordal_km", "res_lat_chordal", "res_lon_chordal", "bur_lat_chordal", "bur_lon_chordal",
                "dist_median_km", "res_lat_median", "res_lon_median", "bur_lat_median", "bur_lon_median",
                "dist_arith_primary_km", "res_lat_arith", "res_lon_arith", "bur_lat_arith", "bur_lon_arith"])
    w.writerows(sens_rows)

# ---------- report ----------
print("\nArithmetic (primary) double-centroid distances (km), first -> last, and full trajectories:")
for area in BURDEN:
    ds = []
    for p in PERIODS:
        bla, blo = med_bur[(area, p)]; rla, rlo = med_res[(area, p)]
        ds.append(hav(bla, blo, rla, rlo))
    mono = all(ds[i] >= ds[i + 1] for i in range(5))
    print(f"  {area:<22} {ds[0]:>7.0f} -> {ds[-1]:>7.0f}  ({(ds[-1]-ds[0])/ds[0]*100:+.1f}%)  monotone_fall={mono}")
    print(f"      trajectory: {' / '.join(f'{d:.0f}' for d in ds)}")
print("\nArithmetic (primary) research centroids, first -> last:")
for area in BURDEN + ["osa", "crs_polyps", "allergic_rhinitis", "tinnitus", "vertigo", "cholesteatoma", "cochlear_implant"]:
    if (area, PERIODS[0]) in med_res:
        a, b = med_res[(area, PERIODS[0])], med_res[(area, PERIODS[-1])]
        print(f"  {area:<22} ({a[0]:.1f},{a[1]:.1f}) -> ({b[0]:.1f},{b[1]:.1f})  drift {hav(*a, *b):.0f} km")
print("\nDONE")

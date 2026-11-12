#!/usr/bin/env python3
"""Estimator comparison for the double-centroid layer (diagnostic, not a freeze).
Estimators: chordal (frozen), spherical geometric median, arithmetic lat + circular lon.
Research weights: data_l3/geo/country_counts.csv. Burden weights: data_l2/raw DALY Number
summed over period years (last period 2020-2023 per amendment v1.1)."""
import csv, math, os
from collections import defaultdict

ROOT = os.path.expanduser("~/workspace/ent-attention-burden")
ref = {r['iso3']: (float(r['centre_lat']), float(r['centre_lon']))
       for r in csv.DictReader(open(f"{ROOT}/data_l3/geo/ref/country_reference.csv")) if r['centre_lat']}
loc2iso = {r['gbd_location_name']: r['iso3'] for r in csv.DictReader(open(f"{ROOT}/data_l3/geo/ref/gbd_location_iso_map.csv"))}
PERIODS = {"1995-1999": range(1995, 2000), "2000-2004": range(2000, 2005), "2005-2009": range(2005, 2010),
           "2010-2014": range(2010, 2015), "2015-2019": range(2015, 2020), "2020-2024": range(2020, 2024)}
BURDEN = ["otitis_media", "hearing_loss", "larynx_cancer", "oral_cancer",
          "nasopharynx_cancer", "other_pharynx_cancer", "thyroid_cancer"]

def chordal(pts):
    x = y = z = 0.0
    for la, lo, w in pts:
        a, o = math.radians(la), math.radians(lo)
        x += w * math.cos(a) * math.cos(o); y += w * math.cos(a) * math.sin(o); z += w * math.sin(a)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))

def geo_median(pts, iters=300):
    la0, lo0 = chordal(pts)
    la, lo = math.radians(la0), math.radians(lo0)
    P = [(math.radians(a), math.radians(o), w) for a, o, w in pts]
    for _ in range(iters):
        num1 = num2 = den = 0.0
        for a, o, w in P:
            dlon = o - lo
            cosc = max(-1, min(1, math.sin(la) * math.sin(a) + math.cos(la) * math.cos(a) * math.cos(dlon)))
            dist = math.acos(cosc)
            if dist < 1e-9: continue
            sd = max(1e-12, math.sin(dist))
            x = math.cos(a) * math.sin(dlon) / sd * dist
            y = (math.cos(la) * math.sin(a) - math.sin(la) * math.cos(a) * math.cos(dlon)) / sd * dist
            wt = w / dist
            num1 += wt * x; num2 += wt * y; den += wt
        dx, dy = num1 / den, num2 / den
        step = math.hypot(dx, dy)
        if step < 1e-10: break
        ca, sa, cl, sl = math.cos(la), math.sin(la), math.cos(lo), math.sin(lo)
        px, py, pz = ca * cl, ca * sl, sa
        ex, ey, ez = -sl, cl, 0.0
        nx, ny, nz = -sa * cl, -sa * sl, ca
        ux, uy, uz = (ex * dx + nx * dy) / step, (ey * dx + ny * dy) / step, (ez * dx + nz * dy) / step
        cs, sn = math.cos(step), math.sin(step)
        qx, qy, qz = px * cs + ux * sn, py * cs + uy * sn, pz * cs + uz * sn
        la = math.asin(max(-1, min(1, qz))); lo = math.atan2(qy, qx)
    return math.degrees(la), math.degrees(lo)

def arith(pts):
    tw = sum(w for _, _, w in pts)
    lat = sum(la * w for la, _, w in pts) / tw
    sx = sum(w * math.cos(math.radians(lo)) for _, lo, w in pts)
    sy = sum(w * math.sin(math.radians(lo)) for _, lo, w in pts)
    return lat, math.degrees(math.atan2(sy, sx))

def hav(lat1, lon1, lat2, lon2):
    a, b, c, d = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1, math.sqrt(h)))

EST = {"chordal": chordal, "median": geo_median, "arith": arith}

# research weights
res = defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/data_l3/geo/country_counts.csv")):
    if r['area'] in BURDEN and r['iso3'] in ref:
        res[(r['area'], r['period'])].append((ref[r['iso3']][0], ref[r['iso3']][1], int(r['n'])))

# burden weights
bur = {}
for area in BURDEN:
    per = defaultdict(lambda: defaultdict(float))
    with open(f"{ROOT}/data_l2/raw/gbd2023_{area}_dalys_raw.csv") as f:
        for r in csv.DictReader(f):
            if r['metric_name'] != 'Number': continue
            iso = loc2iso.get(r['location_name'])
            if not iso or iso not in ref: continue
            y = int(r['year'])
            for p, yrs in PERIODS.items():
                if y in yrs: per[p][iso] += float(r['val'])
    for p, d in per.items():
        bur[(area, p)] = [(ref[i][0], ref[i][1], w) for i, w in d.items()]

plabels = list(PERIODS)
print(f"{'area':<22} {'estimator':<8} {'dist first':>10} {'dist last':>10} {'change':>8}  research centroid first -> last")
for area in BURDEN:
    for name, fn in EST.items():
        ds = []
        rc = []
        for p in plabels:
            b = fn(bur[(area, p)]); r = fn(res[(area, p)])
            ds.append(hav(b[0], b[1], r[0], r[1])); rc.append(r)
        chg = (ds[-1] - ds[0]) / ds[0] * 100
        print(f"{area:<22} {name:<8} {ds[0]:>10.0f} {ds[-1]:>10.0f} {chg:>7.1f}%  ({rc[0][0]:.1f},{rc[0][1]:.1f}) -> ({rc[-1][0]:.1f},{rc[-1][1]:.1f})")
    print()

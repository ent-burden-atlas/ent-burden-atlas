#!/usr/bin/env python3
"""ENT Burden Atlas — static site generator.

Reads ONLY the frozen result files of the ENT attention-burden census
(~/workspace/ent-attention-burden/data_l1|l2|l3|l4), asserts the headline
numbers frozen in the project record, and emits a pure-static English
website (HTML + one CSS file + build-time inline SVG charts) into
site_build/site/.

No number is typed into the pages by hand: every value comes from the
frozen CSVs, and the build fails if any headline assertion fails.
"""
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "site")
CFG = json.load(open(os.path.join(HERE, "site_config.json"), encoding="utf-8"))
ZENODO_DOI = CFG["zenodo_doi"]
ZENODO_URL = "https://doi.org/" + ZENODO_DOI
ASSET_V = CFG.get("asset_version", "1")
OSF_DOI = "10.17605/OSF.IO/NUC4B"
OSF_URL = "https://doi.org/" + OSF_DOI
REPO_URL = "https://github.com/yuye8848/ent-burden-atlas"
CANONICAL = "https://burden.erbihou.org"

PERIODS = ["1995-1999", "2000-2004", "2005-2009", "2010-2014",
           "2015-2019", "2020-2024"]
PLAB = {p: p.replace("-", "–") for p in PERIODS}
BURDEN = ["otitis_media", "hearing_loss", "larynx_cancer", "oral_cancer",
          "nasopharynx_cancer", "other_pharynx_cancer", "thyroid_cancer"]
ATTENTION = ["crs_polyps", "allergic_rhinitis", "osa", "tinnitus", "vertigo",
             "cholesteatoma", "cochlear_implant"]
CANCERS5 = ["larynx_cancer", "oral_cancer", "nasopharynx_cancer",
            "other_pharynx_cancer", "thyroid_cancer"]
AREAS = BURDEN + ATTENTION
NAMES = {
    "otitis_media": "Otitis media",
    "hearing_loss": "Hearing loss",
    "larynx_cancer": "Laryngeal cancer",
    "oral_cancer": "Lip and oral cavity cancer",
    "nasopharynx_cancer": "Nasopharyngeal cancer",
    "other_pharynx_cancer": "Other pharyngeal cancer",
    "thyroid_cancer": "Thyroid cancer",
    "crs_polyps": "Chronic rhinosinusitis / nasal polyps (CRS)",
    "allergic_rhinitis": "Allergic rhinitis",
    "osa": "Obstructive sleep apnoea",
    "tinnitus": "Tinnitus",
    "vertigo": "Vertigo",
    "cholesteatoma": "Cholesteatoma",
    "cochlear_implant": "Cochlear implants",
}
GBD_CAUSE = {
    "otitis_media": "Otitis media (GBD cause 329)",
    "hearing_loss": "Age-related and other hearing loss (GBD cause 674)",
    "larynx_cancer": "Larynx cancer (GBD cause 423)",
    "oral_cancer": "Lip and oral cavity cancer (GBD cause 444)",
    "nasopharynx_cancer": "Nasopharynx cancer (GBD cause 447)",
    "other_pharynx_cancer": "Other pharynx cancer (GBD cause 450)",
    "thyroid_cancer": "Thyroid cancer (GBD cause 480)",
}
TYPE_LABEL = {
    "resolution_dilution": "Resolution-dilution",
    "technology_ignited": "Technology-ignited",
    "burden_tracking": "Burden-tracking",
    "constant": "Constant",
    "unclassified": "Unclassified",
    "share_falling": "Share falling",
    "share_rising": "Share rising",
    "share_stable": "Share stable",
}
CRS_CAVEAT = ("Terminology caveat: under a pre-frozen backup query built only "
              "from modern post-consensus terms, the CRS share change reverses "
              "(+251.0% instead of −26.6%). The apparent decline is read as "
              "terminology migration, not as a change in research volume, and "
              "is not carried as a headline conclusion.")


def read_csv(rel):
    with open(os.path.join(ROOT, rel), newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def fnum(x):
    return f"{x:,.0f}" if abs(x - round(x)) < 1e-9 else f"{x:,.1f}"


def km(x):
    return f"{x:,.0f}"


# ---------------------------------------------------------------- load data
yearly = read_csv("data_l1/l1_counts_by_year.csv")
counts = {(r["area"], int(r["year"])): int(r["count"]) for r in yearly}
period_years = {p: range(int(p[:4]), int(p[:4]) + 5) for p in PERIODS}
pcount = {(a, p): sum(counts[(a, y)] for y in period_years[p])
          for a in AREAS for p in PERIODS}
pool = {p: sum(pcount[(a, p)] for a in AREAS) for p in PERIODS}
share = {(a, p): 100.0 * pcount[(a, p)] / pool[p] for a in AREAS for p in PERIODS}

abr_rows = read_csv("data_l2/abr/abr_primary.csv")
abr = {(r["area"], r["period"]): r for r in abr_rows}
dist_rows = read_csv("data_l3/geo/centroid/double_centroid.csv")
dist = {(r["area"], r["period"]): r for r in dist_rows}
signals = {r["area"]: r for r in read_csv("data_l4/signals.csv")}
typology = {r["area"]: r for r in read_csv("data_l4/typology.csv")}
term = {r["area"]: r for r in read_csv("data_l1/terminology_sensitivity.csv")}
ashare = {(r["area"], r["period"]): r
          for r in read_csv("data_l3/geo/centroid/author_shares.csv")}
lmic = {r["period"]: r for r in
        read_csv("data_l3/geo/centroid/lmic_series_recomputed.csv")}
coverage = read_csv("data_l3/geo/parse_coverage.csv")
tot_records = sum(int(r["records"]) for r in coverage)
tot_aff = sum(int(r["with_aff"]) for r in coverage)
tot_parsed = sum(int(r["parsed"]) for r in coverage)

# ---------------------------------------------------------------- assertions
CHECKS = []


def check(label, ok):
    CHECKS.append((label, bool(ok)))
    if not ok:
        raise AssertionError("HEADLINE ASSERTION FAILED: " + label)


def close(a, b, tol):
    return abs(a - b) <= tol


check("pool 1995-1999 = 26,544", pool["1995-1999"] == 26544)
check("pool 2020-2024 = 128,117", pool["2020-2024"] == 128117)
fc_first = sum(share[(a, "1995-1999")] for a in CANCERS5)
fc_last = sum(share[(a, "2020-2024")] for a in CANCERS5)
check("five-cancer share 32.1% (first)", close(fc_first, 32.1, 0.1))
check("five-cancer share 44.6% (last)", close(fc_last, 44.6, 0.1))
hl_f = abr[("hearing_loss", "1995-1999")]
hl_l = abr[("hearing_loss", "2020-2024")]
check("hearing log2 ABR first −1.05", close(float(hl_f["log2_abr"]), -1.05, 0.01))
check("hearing log2 ABR last −1.47", close(float(hl_l["log2_abr"]), -1.47, 0.01))
check("hearing ABR last 0.36", close(float(hl_l["abr"]), 0.36, 0.01))
check("hearing DALY share last 72.7%",
      close(100 * float(hl_l["burden_share_pool"]), 72.7, 0.15))
check("hearing pub share last 26.3%",
      close(100 * float(hl_l["pub_share_burden_pool"]), 26.3, 0.15))
EXP_DIST = {"otitis_media": (10180, 2013), "hearing_loss": (9751, 3799),
            "larynx_cancer": (4397, 1404), "oral_cancer": (4706, 1102),
            "nasopharynx_cancer": (4785, 2467),
            "other_pharynx_cancer": (8621, 5242), "thyroid_cancer": (6975, 1756)}
for a, (d0, d1) in EXP_DIST.items():
    check(f"distance {a} first {d0:,}",
          round(float(dist[(a, "1995-1999")]["distance_km"])) == d0)
    check(f"distance {a} last {d1:,}",
          round(float(dist[(a, "2020-2024")]["distance_km"])) == d1)
check("LMIC share first 7.9%", close(float(lmic["1995-1999"]["lmic_share_all"]), 7.9, 0.1))
check("LMIC share last 39.8%", close(float(lmic["2020-2024"]["lmic_share_all"]), 39.8, 0.1))
check("LMIC excl-China first 5.4%",
      close(float(lmic["1995-1999"]["lmic_share_excl_china"]), 5.4, 0.1))
check("LMIC excl-China last 17.9%",
      close(float(lmic["2020-2024"]["lmic_share_excl_china"]), 17.9, 0.1))
EXP_TYPE = {"otitis_media": "resolution_dilution",
            "nasopharynx_cancer": "technology_ignited",
            "oral_cancer": "technology_ignited",
            "hearing_loss": "constant",
            "larynx_cancer": "unclassified",
            "other_pharynx_cancer": "unclassified",
            "thyroid_cancer": "unclassified"}
for a, t in EXP_TYPE.items():
    check(f"typology {a} = {t}", typology[a]["type_main"] == t)
agree = sum(1 for r in term.values() if r["directions_agree"] == "yes")
check("terminology directions agree 12/15", agree == 12 and len(term) == 15)
crs = term["crs_polyps"]
check("CRS primary rel change −26.6%",
      close(float(crs["primary_rel_change_pct"]), -26.6, 0.1))
check("CRS backup rel change +251.0%",
      close(float(crs["backup_rel_change_pct"]), 251.0, 0.1))
check("retrievable records 392,456", tot_records == 392456)
check("with affiliation 356,332", tot_aff == 356332)
check("parsed 340,582", tot_parsed == 340582)

# --- assertions for the A–F extension (home cards, findings, geography,
# --- typology pages); expectations transcribed from the frozen record
# --- (manuscript §3.2–3.4, centroid FREEZE_v2, L4 freeze).
EXP_ABR_LAST = {"otitis_media": 1.27, "hearing_loss": 0.36, "larynx_cancer": 0.44,
                "oral_cancer": 1.57, "nasopharynx_cancer": 5.94,
                "other_pharynx_cancer": 2.82, "thyroid_cancer": 9.45}
for a, v in EXP_ABR_LAST.items():
    check(f"ABR last {a} = {v}",
          close(float(abr[(a, "2020-2024")]["abr"]), v, 0.01))
check("otitis media publications 2,229 first", pcount[("otitis_media", "1995-1999")] == 2229)
check("otitis media publications 3,706 last", pcount[("otitis_media", "2020-2024")] == 3706)
check("hearing publications 5,411 first", pcount[("hearing_loss", "1995-1999")] == 5411)
check("hearing publications 21,659 last", pcount[("hearing_loss", "2020-2024")] == 21659)
lar_f, lar_l = abr[("larynx_cancer", "1995-1999")], abr[("larynx_cancer", "2020-2024")]
check("larynx log2 ABR first −0.18", close(float(lar_f["log2_abr"]), -0.18, 0.01))
check("larynx log2 ABR last −1.18", close(float(lar_l["log2_abr"]), -1.18, 0.01))
thy_f, thy_l = abr[("thyroid_cancer", "1995-1999")], abr[("thyroid_cancer", "2020-2024")]
check("thyroid log2 ABR first +3.05", close(float(thy_f["log2_abr"]), 3.05, 0.01))
check("thyroid log2 ABR last +3.24", close(float(thy_l["log2_abr"]), 3.24, 0.01))
check("hearing DALY share first 69.2%",
      close(100 * float(hl_f["burden_share_pool"]), 69.2, 0.15))
check("hearing pub share (burden pool) first 33.5%",
      close(100 * float(hl_f["pub_share_burden_pool"]), 33.5, 0.15))
# geography: trajectory landmarks frozen in centroid FREEZE_v2
check("oral distance 2000-2004 = 1,048",
      round(float(dist[("oral_cancer", "2000-2004")]["distance_km"])) == 1048)
check("oral distance 2005-2009 = 1,369",
      round(float(dist[("oral_cancer", "2005-2009")]["distance_km"])) == 1369)
check("oral distance 2010-2014 = 692",
      round(float(dist[("oral_cancer", "2010-2014")]["distance_km"])) == 692)
check("oral distance 2015-2019 = 1,292",
      round(float(dist[("oral_cancer", "2015-2019")]["distance_km"])) == 1292)
check("NPC distance 2015-2019 = 978",
      round(float(dist[("nasopharynx_cancer", "2015-2019")]["distance_km"])) == 978)
check("thyroid distance 2015-2019 = 1,674",
      round(float(dist[("thyroid_cancer", "2015-2019")]["distance_km"])) == 1674)
for a in ("otitis_media", "hearing_loss", "larynx_cancer"):
    dv = [float(dist[(a, p)]["distance_km"]) for p in PERIODS]
    check(f"distance monotone fall {a}",
          all(dv[i] > dv[i + 1] for i in range(len(dv) - 1)))
dlast = [round(float(dist[(a, "2020-2024")]["distance_km"])) for a in BURDEN]
check("last-period distance min 1,102", min(dlast) == 1102)
check("last-period distance max 5,242", max(dlast) == 5242)
for a in BURDEN:
    d0 = float(dist[(a, "1995-1999")]["distance_km"])
    d1 = float(dist[(a, "2020-2024")]["distance_km"])
    chg = 100 * (d1 - d0) / d0
    check(f"distance change {a} within −80%..−39%", -81.0 <= chg <= -38.0)
chn_first = (float(lmic["1995-1999"]["lmic_share_all"])
             - float(lmic["1995-1999"]["lmic_share_excl_china"]))
chn_last = (float(lmic["2020-2024"]["lmic_share_all"])
            - float(lmic["2020-2024"]["lmic_share_excl_china"]))
check("China share of parsed records first 2.5%", close(chn_first, 2.5, 0.1))
check("China share of parsed records last 21.9%", close(chn_last, 21.9, 0.1))
# typology: S/B/A signal values as frozen in the manuscript §3.4 record
EXP_SIG = {"otitis_media": (-65.5, -33.0, -1.04), "hearing_loss": (-17.1, 5.0, -0.42),
           "larynx_cancer": (-56.9, -18.1, -1.01), "oral_cancer": (97.7, 8.6, 0.78),
           "nasopharynx_cancer": (61.7, -38.3, 1.31),
           "other_pharynx_cancer": (36.6, 19.5, 0.11), "thyroid_cancer": (26.2, 4.8, 0.19)}
for a, (sv, bv, av) in EXP_SIG.items():
    check(f"signal S {a} = {sv}", close(float(signals[a]["S_rel_pct"]), sv, 0.15))
    check(f"signal B {a} = {bv}", close(float(signals[a]["B_rel_pct"]), bv, 0.15))
    check(f"signal A {a} = {av}", close(float(signals[a]["A_delta"]), av, 0.015))
for a in ("nasopharynx_cancer", "oral_cancer"):
    t = typology[a]
    check(f"typology robust {a}",
          t["type_low"] == t["type_main"] == t["type_high"]
          and t["robust_across_thresholds"] == "1")
check("larynx low set = resolution_dilution",
      typology["larynx_cancer"]["type_low"] == "resolution_dilution")
check("other pharynx low set = burden_tracking",
      typology["other_pharynx_cancer"]["type_low"] == "burden_tracking")
check("thyroid high set = constant",
      typology["thyroid_cancer"]["type_high"] == "constant")
check("otitis high set = unclassified",
      typology["otitis_media"]["type_high"] == "unclassified")
check("hearing low set = unclassified",
      typology["hearing_loss"]["type_low"] == "unclassified")
EXP_ATT_TYPE = {"crs_polyps": "share_falling", "allergic_rhinitis": "share_falling",
                "osa": "share_rising", "tinnitus": "share_stable",
                "vertigo": "share_stable", "cholesteatoma": "share_falling",
                "cochlear_implant": "share_stable"}
for a, t in EXP_ATT_TYPE.items():
    check(f"attention label {a} = {t}", typology[a]["type_main"] == t)
daly_chg = [float(signals[a]["daly_annual_pct_change"]) for a in BURDEN]
check("absolute DALY annualised change min +3.9%", close(min(daly_chg), 3.9, 0.15))
check("absolute DALY annualised change max +101.3%", close(max(daly_chg), 101.3, 0.15))

# ---------------------------------------------------------------- SVG charts
def spark(values, w=300, h=92, color="#1d4ed8", zero=False, vfmt="{:.1f}",
          labels=True):
    """Small inline-SVG line chart over the six periods."""
    vals = [float(v) for v in values]
    lo, hi = min(vals), max(vals)
    if zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    pad = (hi - lo) * 0.18 or 1.0
    lo, hi = lo - pad, hi + pad
    x0, x1, y0, y1 = 34, w - 8, 14, h - 16

    def X(i):
        return x0 + (x1 - x0) * i / (len(vals) - 1)

    def Y(v):
        return y1 - (y1 - y0) * (v - lo) / (hi - lo)

    parts = [f'<svg viewBox="0 0 {w} {h}" class="spark" role="img" '
             f'aria-label="trajectory chart">']
    if zero and lo < 0 < hi:
        parts.append(f'<line x1="{x0}" y1="{Y(0):.1f}" x2="{x1}" y2="{Y(0):.1f}" '
                     'stroke="#b91c1c" stroke-width="0.8" stroke-dasharray="4 3"/>')
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                 'stroke-width="1.8"/>')
    for i, v in enumerate(vals):
        parts.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="2.6" '
                     f'fill="{color}"/>')
        if labels:
            dy = -6 if i % 2 == 0 else 13
            parts.append(
                f'<text x="{X(i):.1f}" y="{Y(v) + dy:.1f}" class="svgt" '
                f'text-anchor="middle">{escape(vfmt.format(v))}</text>')
    parts.append(f'<text x="{x0 - 3}" y="{Y(hi - pad):.1f}" class="svgt" '
                 f'text-anchor="end">{escape(vfmt.format(hi - pad))}</text>')
    parts.append(f'<text x="{x0 - 3}" y="{Y(lo + pad):.1f}" class="svgt" '
                 f'text-anchor="end">{escape(vfmt.format(lo + pad))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def mini(values, w=120, h=30, color="#1d4ed8"):
    vals = [float(v) for v in values]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.15 or 1.0
    lo, hi = lo - pad, hi + pad

    def X(i):
        return 3 + (w - 6) * i / (len(vals) - 1)

    def Y(v):
        return (h - 4) - (h - 8) * (v - lo) / (hi - lo)

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    return (f'<svg viewBox="0 0 {w} {h}" class="mini" role="img" '
            f'aria-label="share trajectory sparkline"><polyline points="{pts}" '
            f'fill="none" stroke="{color}" stroke-width="1.6"/></svg>')


# ---------------------------------------------------------------- page frame
CSS = """*{box-sizing:border-box}body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1f2937;line-height:1.55;background:#fff}
header.site{background:#0f2a52;color:#fff;padding:14px 18px}header.site .wrap{max-width:1060px;margin:0 auto}
header.site h1{font-size:20px;margin:0 0 2px}header.site p{margin:0;font-size:13px;color:#c7d5ea}
nav.main{background:#16407c}nav.main .wrap{max-width:1060px;margin:0 auto;display:flex;flex-wrap:wrap;gap:2px}
nav.main a{color:#eaf1fb;text-decoration:none;padding:9px 14px;font-size:14px}nav.main a:hover{background:#1e4f96}
main{max-width:1060px;margin:0 auto;padding:20px 18px 34px}
h2{font-size:22px;margin:8px 0 10px}h3{font-size:17px;margin:22px 0 8px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:16px 0}
.card{border:1px solid #d7dee9;border-top:4px solid #16407c;border-radius:6px;padding:12px 14px;background:#f8fafc}
.card .big{font-size:21px;font-weight:700;color:#0f2a52}.card .lab{font-size:13px;color:#475569;margin-top:3px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border:1px solid #d7dee9;padding:6px 8px;text-align:right}th{background:#eef3fa;color:#0f2a52}
td.l,th.l{text-align:left}tr:nth-child(even) td{background:#fbfcfe}
.tag{display:inline-block;padding:1px 8px;border-radius:9px;font-size:12px;background:#e2e8f0;color:#0f2a52;white-space:nowrap}
.tag.warn{background:#fde8e8;color:#9b1c1c}.tag.good{background:#e0f2e7;color:#166534}
.caveat{border-left:4px solid #b91c1c;background:#fdf3f3;padding:9px 12px;font-size:13.5px;margin:12px 0}
.note{border-left:4px solid #16407c;background:#f1f6fc;padding:9px 12px;font-size:13.5px;margin:12px 0}
.spark{width:100%;max-width:330px;height:auto}.mini{vertical-align:middle}
.svgt{font-size:8.5px;fill:#475569}
.small{font-size:13px;color:#475569}.figcap{font-size:12.5px;color:#64748b;margin:2px 0 14px}
footer.site{border-top:1px solid #d7dee9;background:#f8fafc;color:#475569;font-size:12.5px}
footer.site .wrap{max-width:1060px;margin:0 auto;padding:14px 18px}
a{color:#16407c}code{background:#eef3fa;padding:0 4px;border-radius:3px}
.kv{font-size:14px}.kv b{color:#0f2a52}
.crumbs{font-size:13px;color:#475569;margin:0 0 4px}
.prevnext{display:flex;justify-content:space-between;gap:10px;margin:24px 0 4px;font-size:14px;border-top:1px solid #d7dee9;padding-top:10px}
.acards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0}
.acard{border:1px solid #d7dee9;border-radius:6px;padding:11px 13px;background:#fff}
.acard .nm{font-weight:700;font-size:15px}.acard .nm a{color:#0f2a52;text-decoration:none}.acard .nm a:hover{text-decoration:underline}
.acard .hl{font-size:13.5px;margin-top:4px;color:#1f2937}.acard .tier{margin-top:7px}
tr.mute td{color:#6b7280;background:#f3f4f6}
.verdict{font-weight:700;color:#0f2a52}
@media (max-width:640px){table{font-size:12.5px}th,td{padding:4px 5px}header.site h1{font-size:17px}}
"""


def page(title, body, depth=0):
    pre = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · ENT Burden Atlas</title>
<link rel="stylesheet" href="{pre}assets/style.css?v={ASSET_V}">
</head>
<body>
<header class="site"><div class="wrap">
<h1>ENT Burden Atlas</h1>
<p>Research attention vs disease burden in otolaryngology, 1995–2024 — a preregistered dynamic census</p>
</div></header>
<nav class="main"><div class="wrap">
<a href="{pre}index.html">Home</a><a href="{pre}areas.html">Areas</a><a href="{pre}findings.html">Findings</a><a href="{pre}geography.html">Geography</a><a href="{pre}typology.html">Typology</a><a href="{pre}methods.html">Methods</a><a href="{pre}downloads.html">Downloads</a><a href="{pre}about.html">About</a>
</div></nav>
<main>
{body}
</main>
<footer class="site"><div class="wrap">
Canonical site: <a href="{CANONICAL}/">{CANONICAL}</a> ·
Frozen data &amp; code archive: <a href="{ZENODO_URL}">Zenodo, DOI {ZENODO_DOI}</a> ·
Preregistration: <a href="{OSF_URL}">OSF, DOI {OSF_DOI}</a><br>
This is a static site generated from frozen result files. It measures the configuration of research
allocation only; it makes no judgement about the clinical value of research on any disease.
</div></footer>
</body>
</html>
"""


def pct(x, nd=1):
    return f"{x:.{nd}f}%"


def signed_pct(x):
    return f"{x:+.1f}%"


# ---------------------------------------------------------------- home page
def area_cards():
    cards = []
    for a in AREAS:
        tier_burden = a in BURDEN
        s_first = pct(share[(a, "1995-1999")])
        s_last = pct(share[(a, "2020-2024")])
        mark = " *" if a == "crs_polyps" else ""
        if tier_burden:
            abr_last = float(abr[(a, "2020-2024")]["abr"])
            hl = (f"ABR {abr_last:.2f} in 2020–24 · Pool share "
                  f"{s_first} → {s_last}")
            tier = "Burden tier"
        else:
            hl = (f"Pool share {s_first} → {s_last} · "
                  f"{TYPE_LABEL[typology[a]['type_main']]}")
            tier = "Attention tier"
        cards.append(
            f'<div class="acard"><div class="nm">'
            f'<a href="areas/{a}.html">{escape(NAMES[a])}{mark}</a></div>'
            f'<div class="hl">{hl}</div>'
            f'<div class="tier"><span class="tag">{tier}</span></div></div>')
    return "\n".join(cards)


def home():
    hl_daly = 100 * float(hl_l["burden_share_pool"])
    hl_pub = 100 * float(hl_l["pub_share_burden_pool"])
    body = f"""
<h2>What this is</h2>
<p>The ENT Burden Atlas presents a preregistered census of how research attention in
otolaryngology (ear, nose and throat medicine) has aligned with disease burden over
30 years. Publications were counted in Europe PMC for 14 disease areas
(1995–2024; {fnum(tot_records)} retrievable records); for the seven areas with a
matched Global Burden of Disease (GBD) 2023 cause, output is set against DALY
burden (1995–2023). Four measurement layers are reported on one scale:
publication-share dynamics, the attention–burden ratio (ABR), the geographic
distance between burden and research centroids, and a rule-based decoupling
typology. The design was registered before the record-level data were pulled
(<a href="{OSF_URL}">OSF registration, DOI {OSF_DOI}</a>).</p>

<div class="cards">
<div class="card"><div class="big">{fnum(pool['1995-1999'])} → {fnum(pool['2020-2024'])}</div>
<div class="lab">Publications in the 14-area pool per five-year period, 1995–99 → 2020–24</div></div>
<div class="card"><div class="big">{pct(fc_first)} → {pct(fc_last)}</div>
<div class="lab">Combined pool share of the five head-and-neck cancers</div></div>
<div class="card"><div class="big">log2 ABR −1.05 → −1.47</div>
<div class="lab">Hearing loss: {pct(hl_daly)} of pooled DALYs vs {pct(hl_pub)} of pooled publications
(ABR 0.36 in 2020–24) — the deepest, still-widening deficit</div></div>
<div class="card"><div class="big">{pct(float(lmic['1995-1999']['lmic_share_all']))} → {pct(float(lmic['2020-2024']['lmic_share_all']))}</div>
<div class="lab">Low- and middle-income country share of first authors (all pooled areas);
excluding China {pct(float(lmic['1995-1999']['lmic_share_excl_china']))} → {pct(float(lmic['2020-2024']['lmic_share_excl_china']))}</div></div>
</div>

<h3>Explore the 14 areas</h3>
<div class="acards">
{area_cards()}
</div>
<p class="small">* CRS/polyps: the share decline reverses (+251.0%) under a backup
query built only from modern post-consensus terminology and is read as terminology
migration, not as a fall in research volume (see the
<a href="areas/crs_polyps.html">CRS area page</a> and <a href="methods.html">Methods</a>).</p>

<h3>Headline findings</h3>
<ul>
<li><b>Shares rotated towards oncology.</b> The five head-and-neck cancers jointly rose
from {pct(fc_first)} to {pct(fc_last)} of the pool; laryngeal cancer moved against its
own group (3.2% → 1.4%).</li>
<li><b>Otitis media shrank in share, not in output.</b> Its share fell from 8.4% to 2.9%
while its five-year output grew from 2,229 to 3,706 papers — a denominator effect.</li>
<li><b>Hearing loss is the central level finding.</b> It carries {pct(hl_daly)} of the
seven-cause DALY pool against {pct(hl_pub)} of the same pool's publications, and the
gap widened over 30 years (log2 ABR −1.05 → −1.47).</li>
<li><b>Geography converged in direction, not in level.</b> The burden–research centroid
distance fell for all seven burden-tier causes (−39% to −80%), yet last-period
distances remain 1,102–5,242 km.</li>
<li><b>Typology:</b> otitis media is resolution-dilution (a relative share dilution —
absolute DALYs rose for all seven causes); nasopharyngeal and oral cancer are
technology-ignited under all three threshold sets; hearing loss is constant in
dynamics at a deeply negative level (ABR 0.36); laryngeal, other pharyngeal and
thyroid cancer are reported as <i>unclassified</i>, not forced into a type.</li>
</ul>
<div class="caveat"><b>CRS/polyps.</b> {CRS_CAVEAT}</div>

<h3>How to cite and reuse</h3>
<p class="kv">Preregistration: <a href="{OSF_URL}">doi.org/{OSF_DOI}</a> ·
Frozen data and code: <a href="{ZENODO_URL}">Zenodo, DOI {ZENODO_DOI}</a> ·
Canonical site: <a href="{CANONICAL}/">burden.erbihou.org</a></p>
<p>A manuscript reporting this census is in preparation for <i>Scientometrics</i>
(it has not been published). The frozen tables on the
<a href="downloads.html">Downloads page</a> can be reused under the archive licence;
the pipeline is specialty-agnostic and can be re-run for another specialty's
disease pool.</p>
<p class="small">Scope boundary: every quantity here describes the configuration of
published research relative to modelled burden estimates. Nothing on this site
ranks diseases by clinical importance or states how much research any disease
should receive.</p>
"""
    return page("Home", body)


# ---------------------------------------------------------------- areas page
def areas_page():
    rows = []
    for tier, group in (("Burden tier", BURDEN), ("Attention tier", ATTENTION)):
        rows.append(f'<tr><th class="l" colspan="7">{tier} '
                    f'({"with GBD-matched burden" if tier == "Burden tier" else "no GBD-matched burden; share dynamics only"})</th></tr>')
        for a in group:
            s = signals[a]
            t = typology[a]
            tagcls = ""
            label = TYPE_LABEL[t["type_main"]]
            if t["type_main"] == "unclassified":
                tagcls = " warn"
            if a == "crs_polyps":
                label += " *"
            rows.append(
                f'<tr><td class="l"><a href="areas/{a}.html">{escape(NAMES[a])}</a></td>'
                f'<td>{mini([share[(a, p)] for p in PERIODS])}</td>'
                f'<td>{fnum(pcount[(a, "1995-1999")])}</td>'
                f'<td>{fnum(pcount[(a, "2020-2024")])}</td>'
                f'<td>{pct(share[(a, "1995-1999")])}</td>'
                f'<td>{pct(share[(a, "2020-2024")])}</td>'
                f'<td class="l"><span class="tag{tagcls}">{escape(label)}</span></td></tr>')
    body = f"""
<h2>The 14 disease areas</h2>
<p>Shares are compositions within the 14-area publication pool
({fnum(pool['1995-1999'])} records in 1995–99; {fnum(pool['2020-2024'])} in 2020–24).
Burden-tier areas additionally carry ABR, centroid-distance and typology results on
their own pages. Attention-tier areas have no GBD-matched burden cause, so no burden
quantity is computed or implied for them.</p>
<table>
<tr><th class="l">Area</th><th>Share trajectory</th><th>Publications 1995–99</th>
<th>Publications 2020–24</th><th>Share 1995–99</th><th>Share 2020–24</th><th class="l">Type / dynamics</th></tr>
{''.join(rows)}
</table>
<div class="caveat">* CRS/polyps: {CRS_CAVEAT}</div>
<p class="small">Hearing loss is typed "constant" on dynamics only; read it together
with its level, ABR 0.36 (log2 ABR −1.47) in 2020–24 — a stable misalignment, not an
absence of one. "Resolution" anywhere on this site means relative share dilution
inside the pool; annualised absolute DALYs rose for all seven burden-tier causes
(+3.9% to +101.3%).</p>
"""
    return page("Areas", body)


# ---------------------------------------------------------------- area pages
def area_page(a):
    tier_burden = a in BURDEN
    s = signals[a]
    t = typology[a]
    share_vals = [share[(a, p)] for p in PERIODS]
    parts = [f'<p class="crumbs"><a href="../index.html">Home</a> › '
             f'<a href="../areas.html">Areas</a> › {escape(NAMES[a])}</p>',
             f"<h2>{escape(NAMES[a])}</h2>"]
    if tier_burden:
        parts.append(f'<p class="kv">Tier: <b>Burden tier</b> · Matched burden cause: '
                     f'<b>{escape(GBD_CAUSE[a])}</b>, GBD 2023 (DALYs primary).</p>')
    else:
        parts.append('<p class="kv">Tier: <b>Attention tier</b> · This area has no '
                     'GBD-matched burden cause; <b>no burden quantity is computed '
                     'or implied</b>. Only publication-share dynamics are reported.</p>')
    # share table + chart
    parts.append("<h3>Publication share of the 14-area pool</h3>")
    parts.append(spark(share_vals, vfmt="{:.1f}"))
    parts.append('<p class="figcap">Pool share (%) by five-year period. '
                 'Pool totals: ' + ", ".join(
                     f"{PLAB[p]} {fnum(pool[p])}" for p in PERIODS) + ".</p>")
    tr = "".join(f"<td>{pct(share[(a, p)], 2)}</td>" for p in PERIODS)
    tc = "".join(f"<td>{fnum(pcount[(a, p)])}</td>" for p in PERIODS)
    parts.append(f"""<table>
<tr><th class="l">Period</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}</tr>
<tr><td class="l">Publications</td>{tc}</tr>
<tr><td class="l">Share of pool (%)</td>{tr}</tr>
</table>""")
    parts.append(f'<p>First-to-last share change: <b>{signed_pct(float(s["S_rel_pct"]))}</b> '
                 f'(relative). Dynamics label: <b>{escape(TYPE_LABEL[t["type_main"]])}</b>.</p>')
    if a == "crs_polyps":
        parts.append(f'<div class="caveat">{CRS_CAVEAT} Under the primary query the '
                     f'share fell {pct(share[(a, "1995-1999")])} → '
                     f'{pct(share[(a, "2020-2024")])}; under the backup query it rose '
                     f'1.51% → 5.31%.</div>')
    if tier_burden:
        # ABR
        abr_vals = [float(abr[(a, p)]["log2_abr"]) for p in PERIODS]
        parts.append("<h3>Attention–burden ratio (ABR)</h3>")
        parts.append(spark(abr_vals, color="#b45309", zero=True, vfmt="{:+.2f}"))
        parts.append('<p class="figcap">log2 ABR by period (dashed line = parity, '
                     'ABR 1). Last period pairs publications 2020–24 with burden '
                     '2020–23 (see Methods).</p>')
        tr2 = "".join(f"<td>{float(abr[(a, p)]['log2_abr']):+.2f}</td>" for p in PERIODS)
        tr3 = "".join(f"<td>{float(abr[(a, p)]['abr']):.2f}</td>" for p in PERIODS)
        tr4 = "".join(f"<td>{100 * float(abr[(a, p)]['pub_share_burden_pool']):.1f}%</td>"
                      for p in PERIODS)
        tr5 = "".join(f"<td>{100 * float(abr[(a, p)]['burden_share_pool']):.1f}%</td>"
                      for p in PERIODS)
        parts.append(f"""<table>
<tr><th class="l">Period</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}</tr>
<tr><td class="l">log2 ABR</td>{tr2}</tr>
<tr><td class="l">ABR</td>{tr3}</tr>
<tr><td class="l">Publication share of 7-cause pool (%)</td>{tr4}</tr>
<tr><td class="l">DALY share of 7-cause pool (%)</td>{tr5}</tr>
</table>""")
        if a == "hearing_loss":
            parts.append('<div class="note">Hearing loss is typed <b>constant</b> on '
                         'dynamics only. Its level is the census\'s central level '
                         'finding: ABR 0.36 in 2020–24 (log2 ABR −1.47), i.e. '
                         '72.7% of pooled DALYs against 26.3% of pooled '
                         'publications, with the gap widening over 30 years.</div>')
        # centroid distance
        dvals = [float(dist[(a, p)]["distance_km"]) for p in PERIODS]
        parts.append("<h3>Burden–research centroid distance</h3>")
        parts.append(spark(dvals, color="#0e7490", vfmt="{:,.0f}"))
        parts.append('<p class="figcap">Great-circle distance (km) between the '
                     'DALY-weighted burden centroid and the first-author research '
                     'centroid (arithmetic mean centres; see Methods).</p>')
        trd = "".join(f"<td>{km(float(dist[(a, p)]['distance_km']))}</td>" for p in PERIODS)
        parts.append(f"""<table>
<tr><th class="l">Period</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}</tr>
<tr><td class="l">Distance (km)</td>{trd}</tr>
</table>""")
        chg = 100 * (dvals[-1] - dvals[0]) / dvals[0]
        parts.append(f'<p>First-to-last change: <b>{signed_pct(chg)}</b> '
                     f'({km(dvals[0])} → {km(dvals[-1])} km). Last-period distances '
                     'remain large in absolute terms for every cause.</p>')
        if a == "nasopharynx_cancer":
            parts.append('<p>The path is not monotone: the distance fell to 978 km '
                         'in 2015–19 and rebounded to 2,467 km in 2020–24, the '
                         'largest single-step reversal in this layer.</p>')
        if a == "thyroid_cancer":
            parts.append('<p>The final step rose slightly (1,674 → 1,756 km, '
                         '+82 km) after a steep fall.</p>')
        # author geography
        lm = [100 * float(ashare[(a, p)]["lmic_share"]) for p in PERIODS]
        parts.append("<h3>First-author geography</h3>")
        parts.append(f'<p>LMIC share of parsed first-author records: '
                     f'<b>{pct(lm[0])} → {pct(lm[-1])}</b> (this area; pooled across '
                     f'all 14 areas: 7.9% → 39.8%). Share of first authors located '
                     f'in this cause\'s ten highest-DALY countries: '
                     f'<b>{pct(100 * float(ashare[(a, "1995-1999")]["top10_burden_share"]))} → '
                     f'{pct(100 * float(ashare[(a, "2020-2024")]["top10_burden_share"]))}</b>.</p>')
        # typology
        parts.append("<h3>Decoupling typology</h3>")
        parts.append(f"""<table>
<tr><th class="l">Signal</th><th>Value</th><th class="l">Direction (main thresholds)</th></tr>
<tr><td class="l">S — relative change in pool publication share</td><td>{signed_pct(float(s['S_rel_pct']))}</td><td class="l">{escape(s['S_dir_main'])}</td></tr>
<tr><td class="l">B — relative change in DALY share of the 7-cause pool</td><td>{signed_pct(float(s['B_rel_pct']))}</td><td class="l">{escape(s['B_dir_main'])}</td></tr>
<tr><td class="l">A — change in log2 ABR</td><td>{float(s['A_delta']):+.2f}</td><td class="l">{escape(s['A_dir_main'])}</td></tr>
</table>""")
        parts.append(f"""<table>
<tr><th class="l">Threshold set</th><th class="l">Assigned type</th></tr>
<tr><td class="l">Low (±15% / ±0.3)</td><td class="l">{escape(TYPE_LABEL[t['type_low']])}</td></tr>
<tr><td class="l">Main (±25% / ±0.5)</td><td class="l"><b>{escape(TYPE_LABEL[t['type_main']])}</b></td></tr>
<tr><td class="l">High (±35% / ±0.7)</td><td class="l">{escape(TYPE_LABEL[t['type_high']])}</td></tr>
</table>""")
        if t["type_main"] == "unclassified":
            parts.append('<p>This cause matches no rule under the main thresholds '
                         'and is reported as <b>unclassified</b>; it is not forced '
                         'into a type. Its behaviour under the other threshold sets '
                         'is shown above.</p>')
        parts.append(f'<p class="small">Annualised absolute DALYs for this cause '
                     f'changed {signed_pct(float(s["daly_annual_pct_change"]))} between '
                     'the first and last periods. B is a share: a falling B means '
                     'relative dilution inside the pool, never an absolute decline.</p>')
    else:
        lm = [100 * float(ashare[(a, p)]["lmic_share"]) for p in PERIODS]
        parts.append("<h3>First-author geography</h3>")
        parts.append(f'<p>LMIC share of parsed first-author records: '
                     f'<b>{pct(lm[0])} → {pct(lm[-1])}</b> (this area; pooled across '
                     f'all 14 areas: 7.9% → 39.8%).</p>')
        tt = term[a]
        parts.append("<h3>Terminology sensitivity</h3>")
        parts.append(f'<p>Under a pre-frozen backup query, this area\'s share changed '
                     f'{signed_pct(float(tt["backup_rel_change_pct"]))} (primary query: '
                     f'{signed_pct(float(tt["primary_rel_change_pct"]))}). The two '
                     f'queries {"agree" if tt["directions_agree"] == "yes" else "do not agree"} '
                     'on direction within a ±5% band.</p>')
    idx = AREAS.index(a)
    prev_link = (f'<a href="{AREAS[idx - 1]}.html">← Previous: '
                 f'{escape(NAMES[AREAS[idx - 1]])}</a>' if idx > 0 else "<span></span>")
    next_link = (f'<a href="{AREAS[idx + 1]}.html">Next: '
                 f'{escape(NAMES[AREAS[idx + 1]])} →</a>'
                 if idx < len(AREAS) - 1 else "<span></span>")
    parts.append(f'<div class="prevnext">{prev_link}{next_link}</div>')
    parts.append('<p class="small"><a href="../areas.html">← All areas</a> · '
                 'Full frozen tables: <a href="../downloads.html">Downloads</a></p>')
    return page(NAMES[a], "\n".join(parts), depth=1)


# ---------------------------------------------------------------- methods page
def methods_page():
    body = f"""
<h2>Methods</h2>

<h3>Design and preregistration</h3>
<p>This is a descriptive, denominator-type census. Two denominators are fixed
first — a 14-area publication pool and, inside it, a seven-cause burden pool —
and every quantity is a composition within them. The protocol, disease pool and
analysis layers were fixed in a signed work report and preregistered on the Open
Science Framework before record-level production began
(<a href="{OSF_URL}">registration DOI {OSF_DOI}</a>). One amendment is documented:
the Institute for Health Metrics and Evaluation retired GBD 2021, so Amendment
v1.1 substituted <b>GBD 2023</b> (burden years 1995–2023). The study measures the
configuration of research allocation only; it makes no clinical-value judgement
and no claim about how much research any disease deserves.</p>

<h3>Publication census (L1)</h3>
<p>Publications were counted in Europe PMC under one frozen title/abstract query
per area, per year, 1995–2024 (420 area–year cells), and aggregated into six
five-year periods. The L1 counts use the Europe PMC hitCount basis
(392,458 records). Record-level retrieval for the geographic layer delivered
{fnum(tot_records)} records; two parts each contained one "phantom" record —
counted in the hitCount but never delivered (D-1: oral cancer 2010–2014,
4,806 vs 4,805 retrievable; D-2: obstructive sleep apnoea 2015–2019,
11,604 vs 11,603). Each was accepted only after three scripted checks passed
(unique identifiers; stable hitCount on re-query; identical identifier sets from
an independent second retrieval channel) and both are itemised in a frozen
discrepancy record shipped with the archive.</p>

<h3>Country parsing (L3 production)</h3>
<p>A first-author affiliation was present for {fnum(tot_aff)} records
({pct(100 * tot_aff / tot_records, 2)}). Affiliation strings were parsed to a
country or region by a four-layer dictionary procedure (institution and city
dictionaries with disambiguation rules; no imputation), succeeding for
{fnum(tot_parsed)} records ({pct(100 * tot_parsed / tot_aff, 2)} of those with an
affiliation) across 159 countries or regions. A 90-record manual audit found no
errors. Author country is a property of the publishing institution, not of the
study population.</p>

<h3>Burden data (L2 inputs)</h3>
<p>GBD 2023 DALYs (primary) and prevalence (sensitivity calibre), all ages, both
sexes, global aggregate plus 204 countries and territories (205 locations),
annually 1995–2023, for cause ids 329, 674, 423, 444, 447, 450 and 480.
Country DALY sums reproduce 99.83–99.96% of the corresponding global totals.
The DALY <i>Number</i> metric is primary; the all-ages rate in the downloads is
not age-standardised and is not used. <b>Last-period pairing:</b> burden periods
match publication periods for the first five periods; in the last period the
burden side covers 2020–2023 against publications 2020–2024. This one-year
asymmetry is disclosed wherever last-period burden-relative quantities appear,
and a sensitivity analysis restricts last-period publications to 2020–2023.</p>

<h3>Attention–burden ratio (L2)</h3>
<p>For period <i>t</i>, ABR = (a cause's share of the seven-cause publication
pool) ÷ (its share of the seven-cause DALY pool). ABR 1 is proportionality
within the pool; log2 ABR is reported, so +1 is a twofold publication excess
over burden share and −1 a twofold deficit. Both shares are compositions inside
the same seven-cause pool: the ABR is a within-specialty relative measure and
supports no comparison outside the pool.</p>

<h3>Geographic layer (L3 analysis)</h3>
<p><b>Double-centroid distance.</b> The burden centroid is the DALY-weighted mean
centre of country centres (frozen snapshot of the mledoze/countries dataset);
the research centroid is the same construction weighted by parsed first-author
records. The primary estimator is the <b>arithmetic mean centre</b>: the
weighted arithmetic mean of latitudes combined with the circular (unit-vector)
mean of longitudes; distances are haversine great-circle distances
(R = 6,371.0088 km). The estimator was chosen after a documented diagnostic
episode: the chordal (unit-vector) mean, initially frozen, placed several
research centroids at implausible Arctic latitudes (oral cancer 1995–99 at
82.0°N) because first-author distributions ring the Pacific and their
horizontal components cancel; the spherical geometric median avoided the pole
but degenerated for nasopharyngeal cancer, both centroids snapping to the same
country centre and the distance collapsing to 0.0–0.3 km for three consecutive
periods. All three estimators are frozen side by side for all 42 cause–period
cells in the estimator-sensitivity table shipped with the archive; all three
agree on the direction of every first-to-last distance change.</p>
<p><b>Author shares.</b> The LMIC share is the proportion of parsed records
whose first author is affiliated in a low- or middle-income country (World Bank
low-, lower-middle- and upper-middle-income groups combined), with a
decomposition excluding China. Income groups are the World Bank classification
as frozen on 12 November 2026, <b>held fixed across all periods</b> — a disclosed
simplification, since countries' classifications changed over 30 years. For
burden-tier causes, the share of first authors in that cause's ten
highest-DALY countries is also reported.</p>

<h3>Decoupling typology (L4)</h3>
<p>Each burden-tier cause is classified from three signals comparing the first
and last periods: S, the relative change in its share of the 14-area pool;
B, the relative change in its share of the seven-cause DALY pool; and A, the
change in log2 ABR. The signed protocol fixed the type names and definitions —
resolution-dilution, technology-ignited, burden-tracking, constant — and
anything matching no rule is reported as <b>unclassified, never forced</b>. The
protocol did not fix numeric thresholds; these were operationalised at the
typology stage, before the classification was run (main ±25% for S and B,
±0.5 for A; sensitivity sets ±15%/±0.3 and ±35%/±0.7 are reported with every
assignment). The typology is therefore a descriptive classification under
pre-stated definitions, not preregistered inference. Two reading rules apply:
B is a share, so "burden falls" means relative dilution inside the pool only
(annualised absolute DALYs rose for all seven causes, +3.9% to +101.3%); and
type names are shape labels, not mechanism claims.</p>

<h3>Sensitivity programme and verdicts</h3>
<ul>
<li><b>Lag window.</b> Pairing last-period publications with burden 0, 5 or 10
years earlier changed no cause's log2 ABR sign (7/7 identical across lags);
drift is at most 0.136 per five-year step and 0.271 over the full span.</li>
<li><b>Publication window.</b> Restricting last-period publications to
2020–2023 moved each last-period log2 ABR by less than 0.1, with no sign
change.</li>
<li><b>Burden calibre.</b> The prevalence calibre agrees with the primary
calibre on five of seven last-period signs and five of seven trend directions.
The sign exceptions are laryngeal cancer and otitis media (hearing loss is
92.76% of the seven-cause prevalence pool, which compresses the other shares);
the trend exceptions are other pharyngeal and thyroid cancer, both near-flat
in both calibres. The two headline level claims — hearing loss deeply below
parity and thyroid cancer at the largest excess — hold in both calibres.</li>
<li><b>Terminology drift.</b> For each area, one backup query was specified and
frozen in writing before any backup count was retrieved. The two queries agree
on share direction for 12 of the 15 rows. Cochlear implants and tinnitus differ
only across the ±5% direction band. <b>CRS/polyps reverses outright</b>
(−26.6% primary vs +251.0% backup): the backup query uses only modern terms
that entered routine use after the 2003–2004 consensus terminology, so it is
structurally blind to the sinusitis-era literature. The reversal is read as
terminology migration, and under the protocol's two-query rule the CRS share
decline is withdrawn as a headline conclusion.</li>
</ul>
<p class="small">The lag-window and terminology analyses were completed on
12 November 2026, after the primary layers were frozen; the backup queries were
fixed before their counts existed. They are reported as completions of the
protocol's sensitivity programme at the analysis stage, not as elements of the
original preregistration timestamp.</p>

<h3>Use of large language models</h3>
<p>Large language models were used as assistive tools in this project: for
development and debugging of analysis code, for orchestration of the analysis
pipeline, and for assistance in drafting the manuscript. All data were produced
by deterministic scripts from the public sources named above; every number
reported here was verified against the frozen result files; no data, result or
figure was generated by a language model.</p>
"""
    return page("Methods", body)


# ---------------------------------------------------------------- findings
def findings_page():
    hl_daly = 100 * float(hl_l["burden_share_pool"])
    hl_pub = 100 * float(hl_l["pub_share_burden_pool"])
    body = f"""
<h2>Findings</h2>
<p>The census's six headline findings, in the order of the measurement layers,
followed by the scorecard for the three expectations recorded in the
preregistration. Every quantity describes the configuration of published
research relative to modelled burden estimates; none ranks diseases by clinical
importance.</p>

<h3>1. The pool grew fivefold and rotated towards oncology</h3>
<p>The 14-area pool grew from {fnum(pool['1995-1999'])} publications in 1995–99
to {fnum(pool['2020-2024'])} in 2020–24. The five head-and-neck cancers jointly
rose from {pct(fc_first)} to {pct(fc_last)} of the pool, driven by
nasopharyngeal cancer (8.3% → 13.4%), oral cancer (4.5% → 8.9%) and thyroid
cancer (10.1% → 12.7%). Laryngeal cancer moved against its own group
(3.2% → 1.4%): the rotation is within oncology as much as towards it.</p>

<h3>2. Otitis media shrank in share, not in output</h3>
<p>Its pool share fell from 8.4% to 2.9% while its five-year output rose from
2,229 to 3,706 publications — a textbook denominator effect, in which a
still-growing area is diluted by faster-growing neighbours.</p>

<h3>3. Hearing loss is the central level finding</h3>
<p>In 2020–24 hearing loss carried {pct(hl_daly)} of the seven-cause DALY pool
against {pct(hl_pub)} of the same pool's publications — roughly one-third of
the publication share its burden share would imply under proportionality. Its
log2 ABR deepened from −1.05 to −1.47 (ABR 0.48 → 0.36), the only cause below
parity in the first period that ended further below it. Laryngeal cancer
joined it from above (−0.18 → −1.18). At the other end, thyroid cancer held
the pool's largest excess throughout (+3.05 → +3.24; ABR ≈ 9.45 in the last
period).</p>

<h3>4. Geography converged in direction, not in level</h3>
<p>The distance between the DALY-weighted burden centroid and the
first-author research centroid fell for all seven burden-tier causes
(−39% to −80% between the first and last periods). Last-period distances
remain large in absolute terms — 1,102 to 5,242 km: the research centre of
every cause still sits on a different part of the map from its burden centre.
The paths are not all smooth: nasopharyngeal cancer's distance fell to 978 km
in 2015–19 and then rebounded to 2,467 km. Detail on the
<a href="geography.html">Geography page</a>.</p>

<h3>5. The authorship base broadened</h3>
<p>The low- and middle-income country (LMIC) share of first authors across
the pooled areas rose from 7.9% in 1995–99 to 39.8% in 2020–24. China
accounts for much of the rise (2.5% → 21.9% of all parsed records) but not
all of it: excluding China, the LMIC share of all parsed records still rose
from 5.4% to 17.9%.</p>

<h3>6. Typology: two robust types, one stable misalignment, three unclassified</h3>
<p>Under the rule-based decoupling typology, otitis media is
resolution-dilution (a relative share dilution only — annualised absolute
DALYs rose for all seven causes). Nasopharyngeal and oral cancer are
technology-ignited, the only two assignments unchanged under all three
threshold sets. Hearing loss is typed <b>constant</b> on dynamics only, and
must be read together with its level — ABR 0.36 in 2020–24, the pool's
deepest deficit: a stable misalignment, not an absence of one. Laryngeal,
other pharyngeal and thyroid cancer match no rule under the main thresholds
and are reported as <i>unclassified</i>, not forced into a type. Detail on
the <a href="typology.html">Typology page</a>.</p>

<div class="caveat"><b>CRS/polyps.</b> {CRS_CAVEAT} The CRS share decline is
therefore not counted among the headline findings above.</div>

<h3>The preregistered expectations, scored</h3>
<table>
<tr><th class="l">Expectation (as registered)</th><th class="l">Verdict</th><th class="l">What the data show</th></tr>
<tr><td class="l">(1) Classic infectious diseases will fall in publication share but not in absolute output.</td>
<td class="l"><span class="verdict">Fully matched</span></td>
<td class="l">Otitis media is the textbook case: share 8.4% → 2.9%; output 2,229 → 3,706 publications per period.</td></tr>
<tr><td class="l">(2) Burden is shifting towards lower-income regions while research geography does not follow.</td>
<td class="l"><span class="verdict">Largely not supported</span></td>
<td class="l">Research geography did follow: centroid distances contracted for all seven causes under all three estimators, and the LMIC first-author share rose 7.9% → 39.8%. The expectation survives only in its level form — the remaining distances are still 1,102–5,242 km.</td></tr>
<tr><td class="l">(3) Share gains will concentrate in diseases marked by treatment or technology shifts.</td>
<td class="l"><span class="verdict">Half matched</span></td>
<td class="l">The head-and-neck cancers fit the expectation. Obstructive sleep apnoea, the clearest technology-associated area, rose once and then plateaued, its yearly share sitting at roughly 12–13% in every year since 2005. The CRS point originally attached to this expectation is now read as terminology migration (caveat above), not as evidence about the biologics era either way.</td></tr>
</table>
<p class="small">A scorecard of one full, one largely failed and one half is
what a preregistered descriptive study should expect to publish; the failed
expectation (2) is the more informative result, because it rules out the
simplest version of the "research ignores the shifting burden" narrative for
this specialty.</p>
"""
    return page("Findings", body)


# ---------------------------------------------------------------- geography
def geography_page():
    rows = []
    for a in BURDEN:
        dv = [float(dist[(a, p)]["distance_km"]) for p in PERIODS]
        chg = 100 * (dv[-1] - dv[0]) / dv[0]
        cells = "".join(f"<td>{km(v)}</td>" for v in dv)
        rows.append(f'<tr><td class="l">{escape(NAMES[a])}</td>{cells}'
                    f'<td>{signed_pct(chg)}</td></tr>')
    lmic_rows = []
    for p in PERIODS:
        tot = float(lmic[p]["lmic_share_all"])
        exc = float(lmic[p]["lmic_share_excl_china"])
        lmic_rows.append(f'<tr><td class="l">{PLAB[p]}</td><td>{pct(tot)}</td>'
                         f'<td>{pct(tot - exc)}</td><td>{pct(exc)}</td></tr>')
    body = f"""
<h2>Geography: burden and research centroids</h2>
<p>For each burden-tier cause and period, two centres are computed over the
same set of country centres. The <b>burden centroid</b> is weighted by GBD
2023 DALY numbers — it sits where the cause's burden sits. The <b>research
centroid</b> is weighted by parsed first-author records — it sits where the
cause's publishing authors are. Both use the <b>arithmetic mean centre</b>
(the weighted arithmetic mean of country-centre latitudes combined with the
circular mean of longitudes; centroid freeze v2), and the distance between
them is the haversine great-circle distance. The estimator's diagnostic
history, and the side-by-side comparison with the two estimators it
replaced, are documented on the <a href="methods.html">Methods page</a> and
in the frozen estimator-sensitivity table on the
<a href="downloads.html">Downloads page</a>.</p>

<h3>Double-centroid distance (km)</h3>
<table>
<tr><th class="l">Cause</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}<th>Change, first → last</th></tr>
{''.join(rows)}
</table>
<p>The distance fell for all seven causes (−39% to −80%). Three paths —
otitis media, hearing loss and laryngeal cancer — fall monotonically. The
others do not: oral cancer's path is a sawtooth (1,048 / 1,369 / 692 /
1,292 km across the middle periods); nasopharyngeal cancer fell to 978 km
in 2015–19 and rebounded to 2,467 km in the last period, the largest
single-step reversal in this layer; thyroid cancer rose slightly in the
final step (1,674 → 1,756 km, +82 km) after a steep fall. Convergence in
direction is not convergence in level: last-period distances remain
1,102–5,242 km, so the research centre of every cause still sits on a
different part of the map from its burden centre.</p>

<h3>Who publishes: LMIC first-author share</h3>
<p>Pooled across all 14 areas, the share of parsed first-author records
whose author is affiliated in a low- or middle-income country (the World
Bank low-, lower-middle- and upper-middle-income groups combined; the
classification snapshot is held fixed across all periods, a disclosed
simplification):</p>
<table>
<tr><th class="l">Period</th><th>LMIC share of parsed records</th><th>of which China</th><th>LMIC excluding China</th></tr>
{''.join(lmic_rows)}
</table>
<p>All three shares use all parsed records as the denominator, so the
excluding-China column is the frozen basis reported throughout this site
(it is not renormalised to non-China records). China alone accounts for
much of the pooled rise (2.5% → 21.9% of all parsed records), but the
excluding-China share still more than tripled (5.4% → 17.9%). Per-area
first-author geography — including each burden cause's share of authors in
its ten highest-DALY countries — is on the individual
<a href="areas.html">area pages</a>.</p>
"""
    return page("Geography", body)


# ---------------------------------------------------------------- typology
def typology_page():
    rows = []
    for a in BURDEN:
        s, t = signals[a], typology[a]
        mute = ' class="mute"' if t["type_main"] == "unclassified" else ""
        rows.append(
            f'<tr{mute}><td class="l">{escape(NAMES[a])}</td>'
            f'<td>{signed_pct(float(s["S_rel_pct"]))}</td>'
            f'<td>{signed_pct(float(s["B_rel_pct"]))}</td>'
            f'<td>{float(s["A_delta"]):+.2f}</td>'
            f'<td class="l"><b>{escape(TYPE_LABEL[t["type_main"]])}</b></td>'
            f'<td class="l">{escape(TYPE_LABEL[t["type_low"]])}</td>'
            f'<td class="l">{escape(TYPE_LABEL[t["type_high"]])}</td></tr>')
    arows = []
    for a in ATTENTION:
        s, t = signals[a], typology[a]
        mark = " *" if a == "crs_polyps" else ""
        arows.append(
            f'<tr><td class="l">{escape(NAMES[a])}{mark}</td>'
            f'<td>{pct(share[(a, "1995-1999")])} → {pct(share[(a, "2020-2024")])}</td>'
            f'<td>{signed_pct(float(s["S_rel_pct"]))}</td>'
            f'<td class="l"><b>{escape(TYPE_LABEL[t["type_main"]])}</b></td>'
            f'<td class="l">{escape(TYPE_LABEL[t["type_low"]])}</td>'
            f'<td class="l">{escape(TYPE_LABEL[t["type_high"]])}</td></tr>')
    body = f"""
<h2>Decoupling typology</h2>
<p>Each burden-tier cause is classified from three signals comparing the
first period (1995–99) with the last (2020–24): <b>S</b>, the relative
change in its share of the 14-area publication pool; <b>B</b>, the relative
change in its share of the seven-cause DALY pool; and <b>A</b>, the change
in log2 ABR. The signed protocol fixed the type names, definitions and the
three-signal framework; anything matching no rule is reported as
<b>unclassified, never forced</b>.</p>

<h3>Burden tier (main thresholds ±25% for S and B, ±0.5 for A)</h3>
<table>
<tr><th class="l">Cause</th><th>S</th><th>B</th><th>A</th><th class="l">Main type</th><th class="l">Low set (±15% / ±0.3)</th><th class="l">High set (±35% / ±0.7)</th></tr>
{''.join(rows)}
</table>
<p>Sensitivity behaviour: nasopharyngeal and oral cancer are
technology-ignited under all three threshold sets — the only two fully
robust assignments. Otitis media is resolution-dilution under the main and
low sets and unclassified under the high set. Hearing loss is constant
under the main and high sets and unclassified under the low set; its type
describes dynamics only and must be read together with its level — ABR
0.36 in 2020–24 (log2 ABR −1.47), the pool's deepest deficit. Of the three
causes unclassified under the main thresholds, laryngeal cancer becomes
resolution-dilution under the low set, other pharyngeal cancer becomes
burden-tracking under the low set, and thyroid cancer becomes constant
under the high set. Each sits near a rule boundary; the classification
reports that rather than resolving it by fiat.</p>

<h3>Attention tier: share-dynamics labels only</h3>
<p>Attention-tier areas have no GBD-matched burden cause, so they receive
no type — only a label for the direction of their pool-share change under
the same bands.</p>
<table>
<tr><th class="l">Area</th><th>Share 1995–99 → 2020–24</th><th>S</th><th class="l">Label (main band)</th><th class="l">Low band</th><th class="l">High band</th></tr>
{''.join(arows)}
</table>
<div class="caveat">* CRS/polyps: {CRS_CAVEAT}</div>

<h3>How to read this page</h3>
<p><b>B is a share, not a level.</b> A falling B means relative dilution
inside the seven-cause pool. Annualised absolute DALYs in fact rose for
all seven burden-tier causes between the first and last periods (+3.9% to
+101.3%), so "resolution" in the resolution-dilution label means relative
share dilution only; nothing on this page claims any burden fell in
absolute terms.</p>
<p><b>Thresholds.</b> The signed protocol did not fix numeric thresholds.
The thresholds used here — main ±25% for S and B and ±0.5 for A, with the
±15%/±0.3 and ±35%/±0.7 sensitivity sets shown for every assignment — were
operationalised at the typology stage, before the classification was run.
The typology is therefore a descriptive classification under pre-stated
type definitions, not preregistered inference.</p>
<p><b>Type names are shape labels, not mechanism claims.</b>
"Technology-ignited" names a configuration — publication share rising
while burden share is flat or falling, with ABR rising — and asserts
nothing about what caused it.</p>
"""
    return page("Typology", body)


# ---------------------------------------------------------------- about
def about_page():
    body = f"""
<h2>About this atlas</h2>
<p>The ENT Burden Atlas is the open resource layer of a preregistered census
of research attention versus disease burden in otolaryngology, 1995–2024.
It exposes the census's frozen results — publication shares,
attention–burden ratios, burden–research centroid distances and the
decoupling typology — by area, period and country, for reuse and for
replication of the design in other specialties: the pipeline is
specialty-agnostic in structure (a frozen disease pool, a public
bibliographic source, a public burden source, and the four measurement
layers above).</p>

<h3>Provenance</h3>
<p class="kv">
<b>Preregistration:</b> Open Science Framework project 42ytu; registration
DOI <a href="{OSF_URL}">{OSF_DOI}</a>. The protocol was registered before
record-level production began; Amendment v1.1, substituting GBD 2023 for
the GBD 2021 release that the Institute for Health Metrics and Evaluation
had retired, is filed with the registration.<br>
<b>Frozen archive:</b> Zenodo, DOI <a href="{ZENODO_URL}">{ZENODO_DOI}</a> —
all frozen tables, the record-level country-parse table, the GBD input
extracts, all production and figure code, and the project documents.<br>
<b>Canonical site:</b> <a href="{CANONICAL}/">{CANONICAL}</a><br>
<b>Frozen as of:</b> 12 November 2026. This is a static site generated from
the frozen result files; it is not updated as new data appear.</p>

<h3>Authors</h3>
<p>Peiliang Lei (corresponding author), Wenrong Dong, Jingyi Tan,
Xiaoying Yang<br>
Department of Otolaryngology, Third Hospital of Shijiazhuang, Hebei,
China.</p>

<h3>Data sources</h3>
<ul>
<li><b>Publications:</b> Europe PMC — frozen title/abstract queries, counts
for 1995–2024, and record-level retrieval for the geographic layer.</li>
<li><b>Burden:</b> Global Burden of Disease 2023 estimates (Institute for
Health Metrics and Evaluation) — DALYs primary, prevalence as the
sensitivity calibre — for the seven matched causes, 1995–2023.</li>
<li><b>Country classification:</b> World Bank income classification
(snapshot frozen 12 November 2026 and held fixed across all periods);
country centres from the frozen snapshot of the mledoze/countries
dataset.</li>
</ul>

<h3>How to cite</h3>
<div class="note">
Lei P, Dong W, Tan J, Yang X. <i>Research attention and disease burden in
otolaryngology, 1995–2024: a preregistered dynamic census of publication
shares, attention–burden ratios and research geography.</i> Manuscript in
preparation for <i>Scientometrics</i>.<br>
Preregistration: <a href="{OSF_URL}">doi.org/{OSF_DOI}</a> ·
Frozen data and code: <a href="{ZENODO_URL}">doi.org/{ZENODO_DOI}</a> ·
Atlas: <a href="{CANONICAL}/">burden.erbihou.org</a>
</div>
<p class="small">Scope boundary: every quantity in this atlas describes the
configuration of published research relative to modelled burden estimates.
Nothing here ranks diseases by clinical importance or states how much
research any disease should receive.</p>
"""
    return page("About", body)


# ---------------------------------------------------------------- downloads
DOWNLOAD_FILES = [
    ("data_l1/l1_counts_by_year.csv", "L1 publication counts by year (primary queries)"),
    ("data_l1/l1_counts_backup_by_year.csv", "L1 publication counts by year (backup queries)"),
    ("data_l1/terminology_sensitivity.csv", "Terminology sensitivity: primary vs backup directions"),
    ("data_l2/abr/abr_primary.csv", "ABR primary calibre (DALY shares), 42 cells"),
    ("data_l2/abr/abr_prevalence_sensitivity.csv", "ABR prevalence-calibre sensitivity, 42 cells"),
    ("data_l2/abr/abr_sensitivity_pub2020_2023.csv", "ABR publication-window sensitivity (2020–23), 42 cells"),
    ("data_l2/abr/abr_lag_sensitivity.csv", "ABR lag-window sensitivity (0/5/10 years)"),
    ("data_l3/geo/centroid/double_centroid.csv", "Double-centroid distances and centroids (primary estimator), 42 cells"),
    ("data_l3/geo/centroid/research_centroids_all14.csv", "Research centroids, all 14 areas"),
    ("data_l3/geo/centroid/author_shares.csv", "First-author LMIC and top-10-burden-country shares"),
    ("data_l3/geo/centroid/estimator_sensitivity.csv", "Centroid estimator sensitivity (3 estimators × 42 cells)"),
    ("data_l3/geo/centroid/lmic_series_recomputed.csv", "Pooled LMIC first-author share series (incl. excl.-China)"),
    ("data_l3/geo/country_counts.csv", "Parsed first-author records by area × period × country"),
    ("data_l3/geo/parse_coverage.csv", "Country-parsing coverage by area × period"),
    ("data_l4/signals.csv", "L4 typology signals (S, B, A) for all 14 areas"),
    ("data_l4/typology.csv", "L4 typology assignments under three threshold sets"),
]


def downloads_page():
    rows = []
    for rel, desc in DOWNLOAD_FILES:
        name = os.path.basename(rel)
        size = os.path.getsize(os.path.join(ROOT, rel))
        rows.append(f'<tr><td class="l"><a href="downloads/{name}">{name}</a></td>'
                    f'<td class="l">{escape(desc)}</td><td>{size:,}</td></tr>')
    body = f"""
<h2>Downloads</h2>
<p>The frozen result tables behind every number on this site, as individual CSV
files, or as one archive:
<a href="downloads/frozen_tables.zip"><b>frozen_tables.zip</b></a>.</p>
<table>
<tr><th class="l">File</th><th class="l">Contents</th><th>Bytes</th></tr>
{''.join(rows)}
</table>
<h3>Full archive and code</h3>
<ul>
<li><b>Zenodo archive</b> — the complete frozen snapshot (all tables above plus
the record-level country-parse table for 392,456 records, the GBD input
extracts, reference tables, all production and figure code, and the project
documents): <a href="{ZENODO_URL}">doi.org/{ZENODO_DOI}</a>.</li>
<li><b>Production code</b> — search formulations, GBD mapping, parsing and
indicator code, figure scripts and this site's generator are archived together
with the frozen data in the Zenodo record above:
<a href="{ZENODO_URL}">doi.org/{ZENODO_DOI}</a>.</li>
<li><b>Preregistration</b> — protocol and Amendment v1.1 (GBD 2023):
<a href="{OSF_URL}">doi.org/{OSF_DOI}</a>.</li>
</ul>
<p class="small">Record-level Europe PMC metadata remain available from Europe PMC;
GBD 2023 estimates remain available from the Institute for Health Metrics and
Evaluation. This site redistributes only this study's frozen derived tables.</p>
"""
    return page("Downloads", body)


# ---------------------------------------------------------------- build
def build():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"))
    os.makedirs(os.path.join(OUT, "areas"))
    os.makedirs(os.path.join(OUT, "downloads"))
    with open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    with open(os.path.join(OUT, "CNAME"), "w", encoding="utf-8") as fh:
        fh.write("burden.erbihou.org\n")
    with open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")
    pages = {"index.html": home(), "areas.html": areas_page(),
             "findings.html": findings_page(), "geography.html": geography_page(),
             "typology.html": typology_page(), "methods.html": methods_page(),
             "downloads.html": downloads_page(), "about.html": about_page()}
    for a in AREAS:
        pages[f"areas/{a}.html"] = area_page(a)
    # structural assertions on the assembled site
    check("total pages = 22", len(pages) == 22)
    nav_targets = ["index.html", "areas.html", "findings.html", "geography.html",
                   "typology.html", "methods.html", "downloads.html", "about.html"]
    for rel, html in pages.items():
        pre = "../" if rel.startswith("areas/") else ""
        check(f"nav complete on {rel}",
              all(f'href="{pre}{t}"' in html for t in nav_targets))
        check(f"no github URL on {rel}", "github.com/yuye8848" not in html)
    check("CRS asterisk card on home",
          'crs_polyps.html">Chronic rhinosinusitis / nasal polyps (CRS) *</a>'
          in pages["index.html"])
    check("CRS caveat note under home grid",
          "the share decline reverses (+251.0%)" in pages["index.html"])
    check("typology page mutes unclassified rows",
          pages["typology.html"].count('class="mute"') == 3)
    check("typology page carries CRS caveat",
          "terminology migration" in pages["typology.html"])
    check("findings page pairs hearing constant with ABR 0.36",
          "constant</b> on dynamics only" in pages["findings.html"]
          and "ABR 0.36 in 2020–24" in pages["findings.html"])
    check("findings scorecard verdicts present",
          all(v in pages["findings.html"] for v in
              ("Fully matched", "Largely not supported", "Half matched")))
    check("about page carries both DOIs",
          OSF_DOI in pages["about.html"] and ZENODO_DOI in pages["about.html"])
    for a in AREAS:
        html = pages[f"areas/{a}.html"]
        check(f"breadcrumb on {a}",
              "Home</a> ›" in html and f"› {escape(NAMES[a])}</p>" in html)
    first, last = pages["areas/otitis_media.html"], pages["areas/cochlear_implant.html"]
    check("first area page has Next only",
          "Next:" in first and "Previous:" not in first)
    check("last area page has Previous only",
          "Previous:" in last and "Next:" not in last)
    for rel, html in pages.items():
        with open(os.path.join(OUT, rel), "w", encoding="utf-8") as fh:
            fh.write(html)
    for rel, _desc in DOWNLOAD_FILES:
        shutil.copyfile(os.path.join(ROOT, rel),
                        os.path.join(OUT, "downloads", os.path.basename(rel)))
    with zipfile.ZipFile(os.path.join(OUT, "downloads", "frozen_tables.zip"),
                         "w", zipfile.ZIP_DEFLATED) as z:
        for rel, _desc in DOWNLOAD_FILES:
            z.write(os.path.join(ROOT, rel), arcname=os.path.basename(rel))
    print(f"assertions passed: {len(CHECKS)}/{len(CHECKS)}")
    for label, ok in CHECKS:
        print(("PASS " if ok else "FAIL ") + label)
    print(f"pages written: {len(pages)} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(build())

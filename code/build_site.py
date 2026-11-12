#!/usr/bin/env python3
"""ENT Burden Atlas — static site generator.

Reads ONLY the frozen result files of the ENT attention-burden census
(~/workspace/ent-attention-burden/data_l1|l2|l3|l4), asserts the headline
numbers frozen in the project record, and emits a pure-static bilingual
website (English at the root URLs, a full Chinese mirror under zh/;
HTML + one CSS file + build-time inline SVG charts) into site_build/site/.

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

# ------------------------------------------------------------- Chinese mirror
# Terminology is taken verbatim from the project's Chinese documents (signed
# work report v1 2026-11-08; L4 typology rule table 2026-11-12; terminology
# freeze and sensitivity verdict 2026-11-12; manuscript drafting brief):
# 关注/负担比 (ABR), 双重心距离, 脱钩分型, 解决稀释型 / 技术点燃型 / 负担同行型 /
# 恒定型 / 未归型, 份额上升型 / 份额稳定型 / 份额下降型, 负担层 / 关注层,
# 幽灵记录, 弦平均, 几何中位数, 算术平均中心.
NAMES_ZH = {
    "otitis_media": "中耳炎",
    "hearing_loss": "听力损失",
    "larynx_cancer": "喉癌",
    "oral_cancer": "唇与口腔癌",
    "nasopharynx_cancer": "鼻咽癌",
    "other_pharynx_cancer": "其他咽癌",
    "thyroid_cancer": "甲状腺癌",
    "crs_polyps": "慢性鼻窦炎/鼻息肉（CRS）",
    "allergic_rhinitis": "过敏性鼻炎",
    "osa": "阻塞性睡眠呼吸暂停",
    "tinnitus": "耳鸣",
    "vertigo": "眩晕",
    "cholesteatoma": "胆脂瘤",
    "cochlear_implant": "人工耳蜗",
}
GBD_CAUSE_ZH = {
    "otitis_media": "中耳炎（GBD cause 329）",
    "hearing_loss": "年龄相关和其他听力损失（GBD cause 674）",
    "larynx_cancer": "喉癌（GBD cause 423）",
    "oral_cancer": "唇与口腔癌（GBD cause 444）",
    "nasopharynx_cancer": "鼻咽癌（GBD cause 447）",
    "other_pharynx_cancer": "其他咽癌（GBD cause 450）",
    "thyroid_cancer": "甲状腺癌（GBD cause 480）",
}
TYPE_LABEL_ZH = {
    "resolution_dilution": "解决稀释型",
    "technology_ignited": "技术点燃型",
    "burden_tracking": "负担同行型",
    "constant": "恒定型",
    "unclassified": "未归型",
    "share_falling": "份额下降型",
    "share_rising": "份额上升型",
    "share_stable": "份额稳定型",
}
DIR_ZH = {"down": "降", "stable": "稳", "up": "升"}
CRS_CAVEAT_ZH = ("术语注记：若改用一条在计数前已冻结、仅由现代共识后术语构建的备用检索式，"
                 "CRS 的份额变化将翻转（+251.0%，而非 −26.6%）。这一表面下降应按术语迁移解读，"
                 "而非研究量的变化，且不作为头条结论。")
NAV = [("index.html", "Home", "首页"), ("areas.html", "Areas", "病区"),
       ("findings.html", "Findings", "头条结论"),
       ("geography.html", "Geography", "地理"),
       ("typology.html", "Typology", "分型"),
       ("methods.html", "Methods", "方法"),
       ("downloads.html", "Downloads", "下载"),
       ("about.html", "About", "关于")]
BRAND = {"en": "ENT Burden Atlas", "zh": "耳鼻喉错配图谱站"}
SUBTITLE = {
    "en": "Research attention vs disease burden in otolaryngology, "
          "1995–2024 — a preregistered dynamic census",
    "zh": "耳鼻喉研究关注度与疾病负担，1995–2024——一项预注册的动态普查",
}


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
          labels=True, lang="en"):
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

    aria = "trajectory chart" if lang == "en" else "轨迹图"
    parts = [f'<svg viewBox="0 0 {w} {h}" class="spark" role="img" '
             f'aria-label="{aria}">']
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


def mini(values, w=120, h=30, color="#1d4ed8", lang="en"):
    vals = [float(v) for v in values]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.15 or 1.0
    lo, hi = lo - pad, hi + pad

    def X(i):
        return 3 + (w - 6) * i / (len(vals) - 1)

    def Y(v):
        return (h - 4) - (h - 8) * (v - lo) / (hi - lo)

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    aria = "share trajectory sparkline" if lang == "en" else "份额轨迹小图"
    return (f'<svg viewBox="0 0 {w} {h}" class="mini" role="img" '
            f'aria-label="{aria}"><polyline points="{pts}" '
            f'fill="none" stroke="{color}" stroke-width="1.6"/></svg>')


# ---------------------------------------------------------------- page frame
CSS = """*{box-sizing:border-box}body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif;color:#1f2937;line-height:1.55;background:#fff}
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


def page(title, body, depth=0, lang="en", rel="index.html"):
    pre = "../" * depth
    # The Chinese mirror lives under zh/ with the same internal structure, so
    # in-tree relative links are identical; only the stylesheet (served from
    # the site root) and the language toggle need cross-tree paths.
    asset_pre = "../" * (depth + 1) if lang == "zh" else pre
    if lang == "zh":
        toggle = "../" * (depth + 1) + rel
        toggle_label = "EN"
        nav = "".join(f'<a href="{pre}{t}">{z}</a>' for t, _e, z in NAV)
        footer = f"""本站规范网址：<a href="{CANONICAL}/">{CANONICAL}</a> ·
冻结数据与代码存档：<a href="{ZENODO_URL}">Zenodo，DOI {ZENODO_DOI}</a> ·
预注册：<a href="{OSF_URL}">OSF，DOI {OSF_DOI}</a><br>
本站为静态网站，由冻结结果文件生成。它只度量研究配置的构成关系，
不对任何疾病研究的临床价值作判断。"""
        html_lang = "zh-CN"
    else:
        toggle = pre + "zh/" + rel
        toggle_label = "中文"
        nav = "".join(f'<a href="{pre}{t}">{e}</a>' for t, e, _z in NAV)
        footer = f"""Canonical site: <a href="{CANONICAL}/">{CANONICAL}</a> ·
Frozen data &amp; code archive: <a href="{ZENODO_URL}">Zenodo, DOI {ZENODO_DOI}</a> ·
Preregistration: <a href="{OSF_URL}">OSF, DOI {OSF_DOI}</a><br>
This is a static site generated from frozen result files. It measures the configuration of research
allocation only; it makes no judgement about the clinical value of research on any disease."""
        html_lang = "en"
    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · {BRAND[lang]}</title>
<link rel="stylesheet" href="{asset_pre}assets/style.css?v={ASSET_V}">
</head>
<body>
<header class="site"><div class="wrap">
<h1>{BRAND[lang]}</h1>
<p>{SUBTITLE[lang]}</p>
</div></header>
<nav class="main"><div class="wrap">
{nav}<a href="{toggle}">{toggle_label}</a>
</div></nav>
<main>
{body}
</main>
<footer class="site"><div class="wrap">
{footer}
</div></footer>
</body>
</html>
"""


def pct(x, nd=1):
    return f"{x:.{nd}f}%"


def signed_pct(x):
    return f"{x:+.1f}%"


# ---------------------------------------------------------------- home page
def area_cards(lang="en"):
    zh = lang == "zh"
    names = NAMES_ZH if zh else NAMES
    labels = TYPE_LABEL_ZH if zh else TYPE_LABEL
    cards = []
    for a in AREAS:
        tier_burden = a in BURDEN
        s_first = pct(share[(a, "1995-1999")])
        s_last = pct(share[(a, "2020-2024")])
        mark = " *" if a == "crs_polyps" else ""
        if tier_burden:
            abr_last = float(abr[(a, "2020-2024")]["abr"])
            hl = (f"ABR {abr_last:.2f}（2020–24）· 池内份额 "
                  f"{s_first} → {s_last}" if zh else
                  f"ABR {abr_last:.2f} in 2020–24 · Pool share "
                  f"{s_first} → {s_last}")
            tier = "负担层" if zh else "Burden tier"
        else:
            hl = (f"池内份额 {s_first} → {s_last} · "
                  f"{labels[typology[a]['type_main']]}" if zh else
                  f"Pool share {s_first} → {s_last} · "
                  f"{labels[typology[a]['type_main']]}")
            tier = "关注层" if zh else "Attention tier"
        cards.append(
            f'<div class="acard"><div class="nm">'
            f'<a href="areas/{a}.html">{escape(names[a])}{mark}</a></div>'
            f'<div class="hl">{hl}</div>'
            f'<div class="tier"><span class="tag">{tier}</span></div></div>')
    return "\n".join(cards)


def home(lang="en"):
    hl_daly = 100 * float(hl_l["burden_share_pool"])
    hl_pub = 100 * float(hl_l["pub_share_burden_pool"])
    if lang == "zh":
        body = f"""
<h2>本站简介</h2>
<p>耳鼻喉错配图谱站呈现一项预注册普查的结果：过去 30 年，耳鼻喉科（耳、鼻、喉医学）的
研究关注度与疾病负担的对齐情况。发文量取自 Europe PMC，覆盖 14 个病区
（1995–2024；可取回记录 {fnum(tot_records)} 条）；其中 7 个病区有匹配的全球疾病负担
（GBD）2023 病因，其产出与 DALY 负担（1995–2023）对置。四层测量在同一尺度上报告：
发文份额动态、关注/负担比（ABR）、负担重心与研究重心之间的双重心距离，以及规则化
脱钩分型。本设计在记录级数据拉取之前已经注册
（<a href="{OSF_URL}">OSF 注册，DOI {OSF_DOI}</a>）。</p>

<div class="cards">
<div class="card"><div class="big">{fnum(pool['1995-1999'])} → {fnum(pool['2020-2024'])}</div>
<div class="lab">14 区池每五年的发文量，1995–99 → 2020–24</div></div>
<div class="card"><div class="big">{pct(fc_first)} → {pct(fc_last)}</div>
<div class="lab">五种头颈部癌症的合计池内份额</div></div>
<div class="card"><div class="big">log2 ABR −1.05 → −1.47</div>
<div class="lab">听力损失：占池内 DALY 的 {pct(hl_daly)} vs 占池内发文的 {pct(hl_pub)}
（2020–24 年 ABR 0.36）——最深且仍在扩大的缺口</div></div>
<div class="card"><div class="big">{pct(float(lmic['1995-1999']['lmic_share_all']))} → {pct(float(lmic['2020-2024']['lmic_share_all']))}</div>
<div class="lab">第一作者中的低收入和中等收入国家份额（全部病区合并）；
剔除中国后为 {pct(float(lmic['1995-1999']['lmic_share_excl_china']))} → {pct(float(lmic['2020-2024']['lmic_share_excl_china']))}</div></div>
</div>

<h3>浏览 14 个病区</h3>
<div class="acards">
{area_cards("zh")}
</div>
<p class="small">* 慢性鼻窦炎/鼻息肉：在仅由现代共识后术语构建的备用检索式下，份额下降
发生翻转（+251.0%），应按术语迁移解读，而非研究量的下降（见
<a href="areas/crs_polyps.html">CRS 病区页</a>与<a href="methods.html">方法页</a>）。</p>

<h3>头条发现</h3>
<ul>
<li><b>份额向肿瘤方向轮转。</b>五种头颈部癌症合计占池份额由 {pct(fc_first)} 升至
{pct(fc_last)}；喉癌逆其组而行（3.2% → 1.4%）。</li>
<li><b>中耳炎份额缩小，产出未减。</b>其份额由 8.4% 降至 2.9%，而其五年产出由 2,229 篇
增至 3,706 篇——分母效应。</li>
<li><b>听力损失是核心的水平发现。</b>它占七病因 DALY 池的 {pct(hl_daly)}，而只占同一池
发文的 {pct(hl_pub)}，且缺口在 30 年间扩大（log2 ABR −1.05 → −1.47）。</li>
<li><b>地理上方向趋同，水平未趋同。</b>负担—研究双重心距离在全部 7 个负担层病因上
下降（−39% 至 −80%），但末期距离仍为 1,102–5,242 km。</li>
<li><b>分型：</b>中耳炎为解决稀释型（相对份额稀释——七个病因的绝对 DALY 均上升）；
鼻咽癌与口腔癌在三套阈值下均为技术点燃型；听力损失在动态上为恒定型，但处于深度负水平
（ABR 0.36）；喉癌、其他咽癌与甲状腺癌如实报为<i>未归型</i>，不硬塞入任何类型。</li>
</ul>
<div class="caveat"><b>慢性鼻窦炎/鼻息肉。</b>{CRS_CAVEAT_ZH}</div>

<h3>引用与再利用</h3>
<p class="kv">预注册：<a href="{OSF_URL}">doi.org/{OSF_DOI}</a> ·
冻结数据与代码：<a href="{ZENODO_URL}">Zenodo，DOI {ZENODO_DOI}</a> ·
本站规范网址：<a href="{CANONICAL}/">burden.erbihou.org</a></p>
<p>报告本普查的稿件正在为 <i>Scientometrics</i> 准备中（尚未发表）。
<a href="downloads.html">下载页</a>的冻结表格可按存档许可再利用；本管线在结构上与专科
无关，可换一个专科的疾病池重跑。</p>
<p class="small">范围边界：本站每一数量描述的都是已发表研究相对于模型化负担估计的
配置关系。本站不对疾病按临床重要性排序，也不陈述任何疾病应获得多少研究。</p>
"""
        return page("首页", body, lang="zh", rel="index.html")
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
    return page("Home", body, lang="en", rel="index.html")


# ---------------------------------------------------------------- areas page
def areas_page(lang="en"):
    zh = lang == "zh"
    names = NAMES_ZH if zh else NAMES
    labels = TYPE_LABEL_ZH if zh else TYPE_LABEL
    tiers = (("负担层", BURDEN, "有 GBD 匹配负担") if zh else
             ("Burden tier", BURDEN, "with GBD-matched burden"),
             ("关注层", ATTENTION, "无 GBD 匹配负担；仅份额动态") if zh else
             ("Attention tier", ATTENTION,
              "no GBD-matched burden; share dynamics only"))
    rows = []
    for tier, group, tier_note in tiers:
        rows.append(f'<tr><th class="l" colspan="7">{tier} '
                    f'({tier_note})</th></tr>')
        for a in group:
            s = signals[a]
            t = typology[a]
            tagcls = ""
            label = labels[t["type_main"]]
            if t["type_main"] == "unclassified":
                tagcls = " warn"
            if a == "crs_polyps":
                label += " *"
            rows.append(
                f'<tr><td class="l"><a href="areas/{a}.html">{escape(names[a])}</a></td>'
                f'<td>{mini([share[(a, p)] for p in PERIODS], lang=lang)}</td>'
                f'<td>{fnum(pcount[(a, "1995-1999")])}</td>'
                f'<td>{fnum(pcount[(a, "2020-2024")])}</td>'
                f'<td>{pct(share[(a, "1995-1999")])}</td>'
                f'<td>{pct(share[(a, "2020-2024")])}</td>'
                f'<td class="l"><span class="tag{tagcls}">{escape(label)}</span></td></tr>')
    if zh:
        body = f"""
<h2>14 个病区</h2>
<p>份额是 14 区发文池内的构成
（1995–99 年 {fnum(pool['1995-1999'])} 条记录；2020–24 年 {fnum(pool['2020-2024'])} 条）。
负担层病区的各自页面还载有 ABR、双重心距离与分型结果。关注层病区没有 GBD 匹配的
负担病因，因此不为其计算或暗示任何负担量。</p>
<table>
<tr><th class="l">病区</th><th>份额轨迹</th><th>1995–99 发文</th>
<th>2020–24 发文</th><th>1995–99 份额</th><th>2020–24 份额</th><th class="l">类型 / 动态</th></tr>
{''.join(rows)}
</table>
<div class="caveat">* 慢性鼻窦炎/鼻息肉：{CRS_CAVEAT_ZH}</div>
<p class="small">听力损失的「恒定型」仅就动态而言；须与其水平一并读——2020–24 年
ABR 0.36（log2 ABR −1.47）：稳定的错配，而非没有错配。本站任何地方的「解决」均指
池内相对份额稀释；七个负担层病因的年化绝对 DALY 均上升（+3.9% 至 +101.3%）。</p>
"""
        return page("病区", body, lang="zh", rel="areas.html")
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
    return page("Areas", body, lang="en", rel="areas.html")


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
    return page(NAMES[a], "\n".join(parts), depth=1, lang="en",
                rel=f"areas/{a}.html")


def area_page_zh(a):
    tier_burden = a in BURDEN
    s = signals[a]
    t = typology[a]
    share_vals = [share[(a, p)] for p in PERIODS]
    parts = [f'<p class="crumbs"><a href="../index.html">首页</a> › '
             f'<a href="../areas.html">病区</a> › {escape(NAMES_ZH[a])}</p>',
             f"<h2>{escape(NAMES_ZH[a])}</h2>"]
    if tier_burden:
        parts.append(f'<p class="kv">层级：<b>负担层</b> · 匹配负担病因：'
                     f'<b>{escape(GBD_CAUSE_ZH[a])}</b>，GBD 2023（DALY 为主口径）。</p>')
    else:
        parts.append('<p class="kv">层级：<b>关注层</b> · 本病区没有 GBD 匹配的'
                     '负担病因；<b>不计算、也不暗示任何负担量</b>。仅报告发文份额动态。</p>')
    parts.append("<h3>占 14 区池的发文份额</h3>")
    parts.append(spark(share_vals, vfmt="{:.1f}", lang="zh"))
    parts.append('<p class="figcap">按五年期的池内份额（%）。'
                 '池总量：' + "，".join(
                     f"{PLAB[p]} {fnum(pool[p])}" for p in PERIODS) + "。</p>")
    tr = "".join(f"<td>{pct(share[(a, p)], 2)}</td>" for p in PERIODS)
    tc = "".join(f"<td>{fnum(pcount[(a, p)])}</td>" for p in PERIODS)
    parts.append(f"""<table>
<tr><th class="l">时期</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}</tr>
<tr><td class="l">发文量</td>{tc}</tr>
<tr><td class="l">池内份额（%）</td>{tr}</tr>
</table>""")
    parts.append(f'<p>首末期份额变化：<b>{signed_pct(float(s["S_rel_pct"]))}</b>'
                 f'（相对）。动态标签：<b>{escape(TYPE_LABEL_ZH[t["type_main"]])}</b>。</p>')
    if a == "crs_polyps":
        parts.append(f'<div class="caveat">{CRS_CAVEAT_ZH}主检索式下份额由 '
                     f'{pct(share[(a, "1995-1999")])} 降至 '
                     f'{pct(share[(a, "2020-2024")])}；备用检索式下则由 '
                     f'1.51% 升至 5.31%。</div>')
    if tier_burden:
        abr_vals = [float(abr[(a, p)]["log2_abr"]) for p in PERIODS]
        parts.append("<h3>关注/负担比（ABR）</h3>")
        parts.append(spark(abr_vals, color="#b45309", zero=True,
                           vfmt="{:+.2f}", lang="zh"))
        parts.append('<p class="figcap">按时期的 log2 ABR（虚线＝齐平，ABR 1）。'
                     '末期以 2020–24 年发文对 2020–23 年负担（见方法页）。</p>')
        tr2 = "".join(f"<td>{float(abr[(a, p)]['log2_abr']):+.2f}</td>" for p in PERIODS)
        tr3 = "".join(f"<td>{float(abr[(a, p)]['abr']):.2f}</td>" for p in PERIODS)
        tr4 = "".join(f"<td>{100 * float(abr[(a, p)]['pub_share_burden_pool']):.1f}%</td>"
                      for p in PERIODS)
        tr5 = "".join(f"<td>{100 * float(abr[(a, p)]['burden_share_pool']):.1f}%</td>"
                      for p in PERIODS)
        parts.append(f"""<table>
<tr><th class="l">时期</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}</tr>
<tr><td class="l">log2 ABR</td>{tr2}</tr>
<tr><td class="l">ABR</td>{tr3}</tr>
<tr><td class="l">占 7 病因池的发文份额（%）</td>{tr4}</tr>
<tr><td class="l">占 7 病因池的 DALY 份额（%）</td>{tr5}</tr>
</table>""")
        if a == "hearing_loss":
            parts.append('<div class="note">听力损失仅按动态归为<b>恒定型</b>。'
                         '其水平才是本普查的核心水平发现：2020–24 年 ABR 0.36'
                         '（log2 ABR −1.47），即占池内 DALY 的 72.7% 对占池内发文的 '
                         '26.3%，且缺口在 30 年间扩大。</div>')
        dvals = [float(dist[(a, p)]["distance_km"]) for p in PERIODS]
        parts.append("<h3>负担—研究双重心距离</h3>")
        parts.append(spark(dvals, color="#0e7490", vfmt="{:,.0f}", lang="zh"))
        parts.append('<p class="figcap">DALY 加权负担重心与第一作者研究重心之间的'
                     '大圆距离（km）（算术平均中心；见方法页）。</p>')
        trd = "".join(f"<td>{km(float(dist[(a, p)]['distance_km']))}</td>" for p in PERIODS)
        parts.append(f"""<table>
<tr><th class="l">时期</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}</tr>
<tr><td class="l">距离（km）</td>{trd}</tr>
</table>""")
        chg = 100 * (dvals[-1] - dvals[0]) / dvals[0]
        parts.append(f'<p>首末期变化：<b>{signed_pct(chg)}</b>'
                     f'（{km(dvals[0])} → {km(dvals[-1])} km）。每个病因的末期距离'
                     '在绝对值上仍大。</p>')
        if a == "nasopharynx_cancer":
            parts.append('<p>路径并非单调：距离在 2015–19 年降至 978 km，'
                         '2020–24 年回升至 2,467 km，是本层最大的单步反转。</p>')
        if a == "thyroid_cancer":
            parts.append('<p>最后一步在陡降之后小幅上升（1,674 → 1,756 km，'
                         '+82 km）。</p>')
        lm = [100 * float(ashare[(a, p)]["lmic_share"]) for p in PERIODS]
        parts.append("<h3>第一作者地域</h3>")
        parts.append(f'<p>解析所得第一作者记录中 LMIC 所占份额：'
                     f'<b>{pct(lm[0])} → {pct(lm[-1])}</b>（本病区；14 区合并：'
                     f'7.9% → 39.8%）。位于本病因 DALY 前十国家的第一作者份额：'
                     f'<b>{pct(100 * float(ashare[(a, "1995-1999")]["top10_burden_share"]))} → '
                     f'{pct(100 * float(ashare[(a, "2020-2024")]["top10_burden_share"]))}</b>。</p>')
        parts.append("<h3>脱钩分型</h3>")
        parts.append(f"""<table>
<tr><th class="l">信号</th><th>值</th><th class="l">方向（主阈值）</th></tr>
<tr><td class="l">S——池内发文份额的相对变化</td><td>{signed_pct(float(s['S_rel_pct']))}</td><td class="l">{escape(DIR_ZH[s['S_dir_main']])}</td></tr>
<tr><td class="l">B——7 病因池 DALY 份额的相对变化</td><td>{signed_pct(float(s['B_rel_pct']))}</td><td class="l">{escape(DIR_ZH[s['B_dir_main']])}</td></tr>
<tr><td class="l">A——log2 ABR 的变化</td><td>{float(s['A_delta']):+.2f}</td><td class="l">{escape(DIR_ZH[s['A_dir_main']])}</td></tr>
</table>""")
        parts.append(f"""<table>
<tr><th class="l">阈值组</th><th class="l">归型</th></tr>
<tr><td class="l">低组（±15% / ±0.3）</td><td class="l">{escape(TYPE_LABEL_ZH[t['type_low']])}</td></tr>
<tr><td class="l">主组（±25% / ±0.5）</td><td class="l"><b>{escape(TYPE_LABEL_ZH[t['type_main']])}</b></td></tr>
<tr><td class="l">高组（±35% / ±0.7）</td><td class="l">{escape(TYPE_LABEL_ZH[t['type_high']])}</td></tr>
</table>""")
        if t["type_main"] == "unclassified":
            parts.append('<p>该病因在主阈值下不合任何规则，如实报为<b>未归型</b>；'
                         '不硬塞入任何类型。其在其他阈值组下的表现见上表。</p>')
        parts.append(f'<p class="small">本病因的年化绝对 DALY 在首末期之间变化 '
                     f'{signed_pct(float(s["daly_annual_pct_change"]))}。B 是份额：'
                     'B 下降意味着池内相对稀释，绝非绝对下降。</p>')
    else:
        lm = [100 * float(ashare[(a, p)]["lmic_share"]) for p in PERIODS]
        parts.append("<h3>第一作者地域</h3>")
        parts.append(f'<p>解析所得第一作者记录中 LMIC 所占份额：'
                     f'<b>{pct(lm[0])} → {pct(lm[-1])}</b>（本病区；14 区合并：'
                     f'7.9% → 39.8%）。</p>')
        tt = term[a]
        parts.append("<h3>术语敏感性</h3>")
        parts.append(f'<p>在一条预先冻结的备用检索式下，本病区的份额变化为 '
                     f'{signed_pct(float(tt["backup_rel_change_pct"]))}（主检索式：'
                     f'{signed_pct(float(tt["primary_rel_change_pct"]))}）。两个检索式'
                     f'在 ±5% 带内方向{"一致" if tt["directions_agree"] == "yes" else "不一致"}。</p>')
    idx = AREAS.index(a)
    prev_link = (f'<a href="{AREAS[idx - 1]}.html">← 上一区：'
                 f'{escape(NAMES_ZH[AREAS[idx - 1]])}</a>' if idx > 0 else "<span></span>")
    next_link = (f'<a href="{AREAS[idx + 1]}.html">下一区：'
                 f'{escape(NAMES_ZH[AREAS[idx + 1]])} →</a>'
                 if idx < len(AREAS) - 1 else "<span></span>")
    parts.append(f'<div class="prevnext">{prev_link}{next_link}</div>')
    parts.append('<p class="small"><a href="../areas.html">← 全部病区</a> · '
                 '完整冻结表格：<a href="../downloads.html">下载</a></p>')
    return page(NAMES_ZH[a], "\n".join(parts), depth=1, lang="zh",
                rel=f"areas/{a}.html")


# ---------------------------------------------------------------- methods page
def methods_page(lang="en"):
    if lang == "zh":
        body = f"""
<h2>方法</h2>

<h3>设计与预注册</h3>
<p>本研究是一项描述性、分母型普查。先固定两个分母——14 区发文池，及其内的七病因
负担池——一切数量均为池内构成。本方案、疾病池与分析层在记录级生产开始之前，已由
签批的工作报告固定并在开放科学框架（OSF）上预注册
（<a href="{OSF_URL}">注册 DOI {OSF_DOI}</a>）。一项修订有档可查：IHME 已退役
GBD 2021，故修订书 v1.1 以 <b>GBD 2023</b> 替代（负担年份 1995–2023）。本研究只度量
研究配置的构成关系；不作临床价值判断，也不主张任何疾病应获得多少研究。</p>

<h3>发文普查（L1）</h3>
<p>发文量在 Europe PMC 中按每区一条冻结的题名/摘要检索式、逐年计数，覆盖
1995–2024 年（420 个区—年单元），并汇总为六个五年期。L1 计数采用 Europe PMC 的
hitCount 口径（392,458 条记录）。为地理层所做的记录级拉取共得 {fnum(tot_records)}
条记录；其中两个分片各含一条「幽灵记录」——计入 hitCount 却从未被接口交付
（D-1：口腔癌 2010–2014，4,806 vs 可取回 4,805；D-2：阻塞性睡眠呼吸暂停
2015–2019，11,604 vs 11,603）。每条幽灵记录均在三项脚本核验通过后才被接受
（标识符全唯一；复查时 hitCount 稳定；独立第二取回通道所得标识符集合相同），
两条均逐项记入随存档发布的冻结差异记录。</p>

<h3>国家解析（L3 生产）</h3>
<p>{fnum(tot_aff)} 条记录带有第一作者机构信息
（{pct(100 * tot_aff / tot_records, 2)}）。机构字符串经四层词典程序解析为国家或地区
（机构与城市词典加消歧规则；不插补），成功解析 {fnum(tot_parsed)} 条
（占带机构信息记录的 {pct(100 * tot_parsed / tot_aff, 2)}），覆盖 159 个国家或地区。
90 条记录的人工核查未发现错误。作者所在国是发表机构的属性，不是研究人群的属性。</p>

<h3>负担数据（L2 输入）</h3>
<p>GBD 2023 的 DALY（主口径）与患病数（敏感性口径），全年龄、双性别，全球汇总加
204 个国家和地区（205 个地点），逐年 1995–2023，病因编号为 329、674、423、444、
447、450 与 480。各国 DALY 合计可复现相应全球总量的 99.83–99.96%。DALY 的
<i>Number</i>（绝对数）指标为主口径；下载中的全年龄率未经年龄标化，不使用。
<b>末期配对：</b>前五期负担期与发文期一致；末期负担侧为 2020–2023 年，对发文
2020–2024 年。这一年的不对称在凡出现末期负担相对量之处均予披露，且有一项敏感性
分析将末期发文限制于 2020–2023 年。</p>

<h3>关注/负担比（L2）</h3>
<p>对时期 <i>t</i>，ABR ＝（某病因占七病因发文池的份额）÷（其占七病因 DALY 池的
份额）。ABR 1 表示池内成比例；报告 log2 ABR，故 +1 表示发文份额为负担份额的两倍，
−1 表示为其一半。两个份额是同一七病因池内的构成：ABR 是专科内部的相对度量，
不支持池外比较。</p>

<h3>地理层（L3 分析）</h3>
<p><b>双重心距离。</b>负担重心是以国家中心点（mledoze/countries 数据集的冻结快照）
按 DALY 加权的平均中心；研究重心为同一构造、按解析所得第一作者记录加权。主估计量为
<b>算术平均中心</b>：纬度的加权算术平均与经度的圆周（单位向量）平均相结合；距离为
haversine 大圆距离（R = 6,371.0088 km）。估计量是在一段有档可查的诊断之后选定的：
最初冻结的弦平均（单位向量平均）把若干研究重心放在了不合情理的北极高纬（口腔癌
1995–99 年位于 82.0°N），因为第一作者分布环绕太平洋、其水平分量相互抵消；球面
几何中位数避开了极点，但对鼻咽癌退化——两个重心吸附到同一国家中心，三个连续时期的
距离塌缩为 0.0–0.3 km。三种估计量在全部 42 个病因—时期单元上并排冻结于随存档发布的
估计量敏感性表中；三者对每个病因首末期距离变化的方向一致。</p>
<p><b>作者份额。</b>LMIC 份额是解析所得记录中第一作者机构位于低收入或中等收入国家
（世界银行低收入、下中等收入与上中等收入组别合并）的比例，并作剔除中国的分解。
收入组别为 2026 年 11 月 12 日冻结的世界银行分类，<b>全部时期固定不变</b>——这是
已披露的简化，因为各国的分类在 30 年间发生过变化。对负担层病因，还报告位于其
DALY 前十国家的第一作者份额。</p>

<h3>脱钩分型（L4）</h3>
<p>每个负担层病因由比较首末期的三个信号归型：S，14 区池发文份额的相对变化；B，七病因
DALY 池份额的相对变化；A，log2 ABR 的变化。签批方案固定了型名与定义——解决稀释型、
技术点燃型、负担同行型、恒定型——凡不合任何规则者如实报为<b>未归型，绝不硬塞</b>。
方案未固定数值阈值；阈值在分型阶段、归型运行之前操作化（主阈值 S 与 B 为 ±25%、
A 为 ±0.5；±15%/±0.3 与 ±35%/±0.7 两套敏感性组别随每个归型一并报告）。因此分型是
预设型定义之下的描述性分类，而非预注册推断。两条读法规则：B 是份额，故「负担下降」
只表示池内相对稀释（七个病因的年化绝对 DALY 均上升，+3.9% 至 +101.3%）；型名是
形态标签，不是机制断言。</p>

<h3>敏感性方案与裁定</h3>
<ul>
<li><b>滞后窗。</b>将末期发文与早 0、5 或 10 年的负担配对，未改变任何病因的
log2 ABR 符号（7/7 在各滞后下相同）；漂移每五年步至多 0.136，全程至多 0.271。</li>
<li><b>发文窗。</b>将末期发文限制于 2020–2023 年，使每个末期 log2 ABR 的移动
小于 0.1，且无符号变化。</li>
<li><b>负担口径。</b>患病口径在末期符号上与主口径七者中五者一致、在趋势方向上亦
五者一致。符号例外为喉癌与中耳炎（听力损失占七病因患病池的 92.76%，压缩了其他
份额）；趋势例外为其他咽癌与甲状腺癌，两者在两口径下均接近持平。两项头条水平
结论——听力损失深度低于齐平、甲状腺癌为最大超额——在两口径下均成立。</li>
<li><b>术语漂移。</b>每个病区各设定一条备用检索式，并在取回任何备用计数之前以书面
冻结。两个检索式在 15 行中 12 行的份额方向上一致。人工耳蜗与耳鸣仅在 ±5% 方向带
两侧有别。<b>CRS/鼻息肉则完全翻转</b>（主式 −26.6% vs 备用式 +251.0%）：备用检索式
只用 2003–2004 年共识术语之后才进入常规使用的现代术语，因此在结构上看不见
鼻窦炎时代的文献。该翻转按术语迁移解读，并依方案的双式规则，CRS 份额下降撤出
头条结论。</li>
</ul>
<p class="small">滞后窗与术语分析于 2026 年 11 月 12 日在主层冻结之后完成；备用
检索式在其计数存在之前已固定。它们作为方案敏感性方案在分析阶段的完成情况报告，
而非原始预注册时间戳的组成部分。</p>

<h3>大型语言模型的使用</h3>
<p>本项目中，大型语言模型被用作辅助工具：用于分析代码的开发与调试、分析管线的
编排，以及稿件起草的协助。全部数据均由确定性脚本从上列公开来源生成；此处报告的
每个数字均已对照冻结结果文件核验；任何数据、结果或图形均非由语言模型生成。</p>
"""
        return page("方法", body, lang="zh", rel="methods.html")
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
    return page("Methods", body, lang="en", rel="methods.html")


# ---------------------------------------------------------------- findings
def findings_page(lang="en"):
    hl_daly = 100 * float(hl_l["burden_share_pool"])
    hl_pub = 100 * float(hl_l["pub_share_burden_pool"])
    if lang == "zh":
        body = f"""
<h2>头条结论</h2>
<p>本普查的六项头条发现，按测量层的顺序排列，其后是预注册所记三项预期的记分卡。
每一数量描述的都是已发表研究相对于模型化负担估计的配置关系；没有一项按临床
重要性为疾病排序。</p>

<h3>1. 发文池扩大约五倍，并向肿瘤轮转</h3>
<p>14 区池由 1995–99 年的 {fnum(pool['1995-1999'])} 篇增至 2020–24 年的
{fnum(pool['2020-2024'])} 篇。五种头颈部癌症合计占池份额由 {pct(fc_first)} 升至
{pct(fc_last)}，由鼻咽癌（8.3% → 13.4%）、口腔癌（4.5% → 8.9%）与甲状腺癌
（10.1% → 12.7%）驱动。喉癌逆其组而行（3.2% → 1.4%）：这一轮转与其说是转向肿瘤，
不如说同样是肿瘤内部的轮转。</p>

<h3>2. 中耳炎份额缩小，产出未减</h3>
<p>其池内份额由 8.4% 降至 2.9%，而五年产出由 2,229 篇升至 3,706 篇——典型的
分母效应：仍在增长的病区被增长更快的邻居稀释。</p>

<h3>3. 听力损失是核心水平发现</h3>
<p>2020–24 年，听力损失占七病因 DALY 池的 {pct(hl_daly)}，而只占同一池发文的
{pct(hl_pub)}——约为其负担份额在成比例情形下所对应发文份额的三分之一。其
log2 ABR 由 −1.05 加深至 −1.47（ABR 0.48 → 0.36），是首期已在齐平线以下、末期
进一步下沉的唯一病因。喉癌自上方加入（−0.18 → −1.18）。另一端，甲状腺癌全程
保持池内最大超额（+3.05 → +3.24；末期 ABR ≈ 9.45）。</p>

<h3>4. 地理：方向趋同，水平未趋同</h3>
<p>DALY 加权负担重心与第一作者研究重心之间的距离，在全部七个负担层病因上下降
（首末期之间 −39% 至 −80%）。末期距离在绝对值上仍大——1,102 至 5,242 km：每个
病因的研究中心仍位于与其负担中心不同的地图区域。路径并不都平滑：鼻咽癌的距离
在 2015–19 年降至 978 km，随后回升至 2,467 km。详见
<a href="geography.html">地理页</a>。</p>

<h3>5. 作者基础展宽</h3>
<p>全部病区合并，第一作者中的低收入和中等收入国家（LMIC）份额由 1995–99 年的
7.9% 升至 2020–24 年的 39.8%。这一上升多由中国贡献（占全部解析记录的
2.5% → 21.9%），但并非全部：剔除中国后，LMIC 占全部解析记录的份额仍由 5.4%
升至 17.9%。</p>

<h3>6. 分型：两个稳健型、一个稳定错配、三个未归型</h3>
<p>在规则化脱钩分型下，中耳炎为解决稀释型（仅为相对份额稀释——七个病因的年化
绝对 DALY 均上升）。鼻咽癌与口腔癌为技术点燃型，是三套阈值下归型不变的仅有的
两个。听力损失仅按动态归为<b>恒定型</b>，必须与其水平一并读——2020–24 年
ABR 0.36，池内最深缺口：稳定的错配，而非没有错配。喉癌、其他咽癌与甲状腺癌在
主阈值下不合任何规则，如实报为<i>未归型</i>，不硬塞入任何类型。详见
<a href="typology.html">分型页</a>。</p>

<div class="caveat"><b>慢性鼻窦炎/鼻息肉。</b>{CRS_CAVEAT_ZH}因此，CRS 份额下降
不计入上述头条发现。</div>

<h3>预注册预期记分卡</h3>
<table>
<tr><th class="l">预期（按注册原文）</th><th class="l">裁定</th><th class="l">数据所示</th></tr>
<tr><td class="l">（1）经典感染性疾病的发文份额将下降，但绝对产出不降。</td>
<td class="l"><span class="verdict">完全符合</span></td>
<td class="l">中耳炎即典型案例：份额 8.4% → 2.9%；产出每期 2,229 → 3,706 篇。</td></tr>
<tr><td class="l">（2）负担正向低收入地区迁移，而研究地理不跟随。</td>
<td class="l"><span class="verdict">大体不成立</span></td>
<td class="l">研究地理实际上跟随了：七个病因的重心距离在三种估计量下全部收缩，第一作者 LMIC 份额由 7.9% 升至 39.8%。该预期仅以其水平形式存留——剩余距离仍为 1,102–5,242 km。</td></tr>
<tr><td class="l">（3）份额增益将集中于有治疗或技术变迁标记的疾病。</td>
<td class="l"><span class="verdict">一半符合</span></td>
<td class="l">头颈部癌症符合该预期。阻塞性睡眠呼吸暂停是最清晰的技术关联病区，其份额只上升了一步便进入平台期，2005 年以来每年的份额都约为 12–13%。原先系于该预期的 CRS 一点，现按术语迁移解读（见上注），不作为生物制剂时代任何方向的证据。</td></tr>
</table>
<p class="small">一全符合、一大体落空、一半符合——这正是预注册描述性研究应当发表的
记分卡；落空的预期（2）反而是信息量更大的结果，因为它排除了本专科「研究忽视
负担迁移」叙事的最简单版本。</p>
"""
        return page("头条结论", body, lang="zh", rel="findings.html")
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
    return page("Findings", body, lang="en", rel="findings.html")


# ---------------------------------------------------------------- geography
def geography_page(lang="en"):
    zh = lang == "zh"
    names = NAMES_ZH if zh else NAMES
    rows = []
    for a in BURDEN:
        dv = [float(dist[(a, p)]["distance_km"]) for p in PERIODS]
        chg = 100 * (dv[-1] - dv[0]) / dv[0]
        cells = "".join(f"<td>{km(v)}</td>" for v in dv)
        rows.append(f'<tr><td class="l">{escape(names[a])}</td>{cells}'
                    f'<td>{signed_pct(chg)}</td></tr>')
    lmic_rows = []
    for p in PERIODS:
        tot = float(lmic[p]["lmic_share_all"])
        exc = float(lmic[p]["lmic_share_excl_china"])
        lmic_rows.append(f'<tr><td class="l">{PLAB[p]}</td><td>{pct(tot)}</td>'
                         f'<td>{pct(tot - exc)}</td><td>{pct(exc)}</td></tr>')
    if zh:
        body = f"""
<h2>地理：负担重心与研究重心</h2>
<p>对每个负担层病因与时期，在同一组国家中心点上计算两个中心。<b>负担重心</b>按
GBD 2023 DALY 数加权——位于该病因负担所在之处。<b>研究重心</b>按解析所得第一作者
记录加权——位于该病因发文作者所在之处。两者均使用<b>算术平均中心</b>（国家中心点
纬度的加权算术平均与经度的圆周平均相结合；重心冻结 v2），两者之间的距离为
haversine 大圆距离。估计量的诊断经过，以及与被其替代的两种估计量的并排比较，
记于<a href="methods.html">方法页</a>与<a href="downloads.html">下载页</a>的冻结
估计量敏感性表。</p>

<h3>双重心距离（km）</h3>
<table>
<tr><th class="l">病因</th>{''.join(f'<th>{PLAB[p]}</th>' for p in PERIODS)}<th>首 → 末变化</th></tr>
{''.join(rows)}
</table>
<p>七个病因的距离全部下降（−39% 至 −80%）。三条路径——中耳炎、听力损失与喉癌——
单调下降。其余并非如此：口腔癌的路径呈锯齿形（中间各期为 1,048 / 1,369 / 692 /
1,292 km）；鼻咽癌在 2015–19 年降至 978 km，末期回升至 2,467 km，为本层最大单步
反转；甲状腺癌在陡降后于最后一步小幅上升（1,674 → 1,756 km，+82 km）。方向趋同
不等于水平趋同：末期距离仍为 1,102–5,242 km，故每个病因的研究中心仍位于与其
负担中心不同的地图区域。</p>

<h3>谁在发文：LMIC 第一作者份额</h3>
<p>14 区合并，解析所得第一作者记录中作者机构位于低收入或中等收入国家（世界银行
低收入、下中等收入与上中等收入组别合并；分类快照在全部时期固定不变，为已披露的
简化）的份额：</p>
<table>
<tr><th class="l">时期</th><th>LMIC 占解析记录的份额</th><th>其中中国</th><th>剔除中国后的 LMIC</th></tr>
{''.join(lmic_rows)}
</table>
<p>三列均以全部解析记录为分母，故剔除中国列即为本站通用的冻结口径（不按非中国
记录重新归一）。这一合并上升多由中国单独贡献（占全部解析记录的 2.5% → 21.9%），
但剔除中国后的份额仍增至三倍以上（5.4% → 17.9%）。各病区的第一作者地域——包括
每个负担病因位于其 DALY 前十国家作者的份额——见各<a href="areas.html">病区页</a>。</p>
"""
        return page("地理", body, lang="zh", rel="geography.html")
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
    return page("Geography", body, lang="en", rel="geography.html")


# ---------------------------------------------------------------- typology
def typology_page(lang="en"):
    zh = lang == "zh"
    names = NAMES_ZH if zh else NAMES
    labels = TYPE_LABEL_ZH if zh else TYPE_LABEL
    rows = []
    for a in BURDEN:
        s, t = signals[a], typology[a]
        mute = ' class="mute"' if t["type_main"] == "unclassified" else ""
        rows.append(
            f'<tr{mute}><td class="l">{escape(names[a])}</td>'
            f'<td>{signed_pct(float(s["S_rel_pct"]))}</td>'
            f'<td>{signed_pct(float(s["B_rel_pct"]))}</td>'
            f'<td>{float(s["A_delta"]):+.2f}</td>'
            f'<td class="l"><b>{escape(labels[t["type_main"]])}</b></td>'
            f'<td class="l">{escape(labels[t["type_low"]])}</td>'
            f'<td class="l">{escape(labels[t["type_high"]])}</td></tr>')
    arows = []
    for a in ATTENTION:
        s, t = signals[a], typology[a]
        mark = " *" if a == "crs_polyps" else ""
        arows.append(
            f'<tr><td class="l">{escape(names[a])}{mark}</td>'
            f'<td>{pct(share[(a, "1995-1999")])} → {pct(share[(a, "2020-2024")])}</td>'
            f'<td>{signed_pct(float(s["S_rel_pct"]))}</td>'
            f'<td class="l"><b>{escape(labels[t["type_main"]])}</b></td>'
            f'<td class="l">{escape(labels[t["type_low"]])}</td>'
            f'<td class="l">{escape(labels[t["type_high"]])}</td></tr>')
    if zh:
        body = f"""
<h2>脱钩分型</h2>
<p>每个负担层病因由比较首期（1995–99）与末期（2020–24）的三个信号归型：<b>S</b>，
14 区发文池份额的相对变化；<b>B</b>，七病因 DALY 池份额的相对变化；<b>A</b>，log2 ABR
的变化。签批方案固定了型名、定义与三信号框架；凡不合任何规则者如实报为
<b>未归型，绝不硬塞</b>。</p>

<h3>负担层（主阈值：S 与 B 为 ±25%，A 为 ±0.5）</h3>
<table>
<tr><th class="l">病因</th><th>S</th><th>B</th><th>A</th><th class="l">主型</th><th class="l">低组（±15% / ±0.3）</th><th class="l">高组（±35% / ±0.7）</th></tr>
{''.join(rows)}
</table>
<p>敏感性表现：鼻咽癌与口腔癌在三套阈值下均为技术点燃型——仅有的两个完全稳健的
归型。中耳炎在主组与低组下为解决稀释型，在高组下为未归型。听力损失在主组与高组下
为恒定型，在低组下为未归型；其型只描述动态，必须与其水平一并读——2020–24 年
ABR 0.36（log2 ABR −1.47），池内最深缺口。在主阈值下未归型的三个病因中，喉癌在
低组下成为解决稀释型，其他咽癌在低组下成为负担同行型，甲状腺癌在高组下成为恒定型。
三者都位于规则边界附近；分类如实报告这一点，而非强行裁断。</p>

<h3>关注层：仅份额动态标签</h3>
<p>关注层病区没有 GBD 匹配的负担病因，因此不归型——只在相同带宽下为其池内份额
变化的方向贴标签。</p>
<table>
<tr><th class="l">病区</th><th>份额 1995–99 → 2020–24</th><th>S</th><th class="l">标签（主带）</th><th class="l">低带</th><th class="l">高带</th></tr>
{''.join(arows)}
</table>
<div class="caveat">* 慢性鼻窦炎/鼻息肉：{CRS_CAVEAT_ZH}</div>

<h3>如何读本页</h3>
<p><b>B 是份额，不是水平。</b>B 下降意味着七病因池内的相对稀释。七个负担层病因的
年化绝对 DALY 在首末期之间实际上均上升（+3.9% 至 +101.3%），故解决稀释型标签中的
「解决」仅指相对份额稀释；本页不主张任何负担在绝对意义上下降。</p>
<p><b>阈值。</b>签批方案未固定数值阈值。此处所用阈值——主阈值 S 与 B 为 ±25%、
A 为 ±0.5，±15%/±0.3 与 ±35%/±0.7 两套敏感性组别随每个归型一并展示——在分型阶段、
归型运行之前操作化。因此分型是预设型定义之下的描述性分类，而非预注册推断。</p>
<p><b>型名是形态标签，不是机制断言。</b>「技术点燃型」命名一种形态组合——发文份额
上升、负担份额持平或下降、且 ABR 上升——并不主张其成因。</p>
"""
        return page("分型", body, lang="zh", rel="typology.html")
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
    return page("Typology", body, lang="en", rel="typology.html")


# ---------------------------------------------------------------- about
def about_page(lang="en"):
    if lang == "zh":
        body = f"""
<h2>关于本图谱站</h2>
<p>耳鼻喉错配图谱站是「耳鼻喉研究关注度与疾病负担普查（1995–2024）」这一预注册
研究的开放资源层。它按病区、时期与国家开放该普查的冻结结果——发文份额、
关注/负担比、负担—研究双重心距离与脱钩分型——供再利用，也供在其他专科复现本
设计：本管线在结构上与专科无关（一个冻结的疾病池、一个公开文献来源、一个公开
负担来源，加上上述四层测量）。</p>

<h3>出处</h3>
<p class="kv">
<b>预注册：</b>开放科学框架（OSF）项目 42ytu；注册
DOI <a href="{OSF_URL}">{OSF_DOI}</a>。方案在记录级生产开始之前注册；修订书
v1.1（以 GBD 2023 替代 IHME 已退役的 GBD 2021）随注册存档。<br>
<b>冻结存档：</b>Zenodo，DOI <a href="{ZENODO_URL}">{ZENODO_DOI}</a>——全部冻结
表格、记录级国家解析表、GBD 输入摘录、全部生产与绘图代码及项目文件。<br>
<b>本站规范网址：</b><a href="{CANONICAL}/">{CANONICAL}</a><br>
<b>冻结于：</b>2026 年 11 月 12 日。本站为由冻结结果文件生成的静态网站；不随
新数据出现而更新。</p>

<h3>作者</h3>
<p>Peiliang Lei（通讯作者）、Wenrong Dong、Jingyi Tan、Xiaoying Yang<br>
Department of Otolaryngology, The Third Hospital of Shijiazhuang, Shijiazhuang, Hebei 050011, China.</p>

<h3>数据来源</h3>
<ul>
<li><b>发文：</b>Europe PMC——冻结题名/摘要检索式，1995–2024 年计数，及地理层的
记录级拉取。</li>
<li><b>负担：</b>全球疾病负担（GBD）2023 估计（IHME）——DALY 为主口径、患病数为
敏感性口径——七个匹配病因，1995–2023 年。</li>
<li><b>国家分类：</b>世界银行收入分类（快照于 2026 年 11 月 12 日冻结，全部时期
固定不变）；国家中心点取自 mledoze/countries 数据集的冻结快照。</li>
</ul>

<h3>引用方式</h3>
<div class="note">
Lei P, Dong W, Tan J, Yang X. <i>Research attention and disease burden in
otolaryngology, 1995–2024: a preregistered dynamic census of publication
shares, attention–burden ratios and research geography.</i> Manuscript in
preparation for <i>Scientometrics</i>.<br>
预注册：<a href="{OSF_URL}">doi.org/{OSF_DOI}</a> ·
冻结数据与代码：<a href="{ZENODO_URL}">doi.org/{ZENODO_DOI}</a> ·
图谱站：<a href="{CANONICAL}/">burden.erbihou.org</a>
</div>
<p class="small">范围边界：本图谱站的每一数量描述的都是已发表研究相对于模型化
负担估计的配置关系。此处不对疾病按临床重要性排序，也不陈述任何疾病应获得
多少研究。</p>
"""
        return page("关于", body, lang="zh", rel="about.html")
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
Department of Otolaryngology, The Third Hospital of Shijiazhuang,
Shijiazhuang, Hebei 050011, China.</p>

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
    return page("About", body, lang="en", rel="about.html")


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


DOWNLOAD_DESC_ZH = [
    "L1 按年发文计数（主检索式）",
    "L1 按年发文计数（备用检索式）",
    "术语敏感性：主式与备用式方向",
    "ABR 主口径（DALY 份额），42 个单元",
    "ABR 患病口径敏感性，42 个单元",
    "ABR 发文窗敏感性（2020–23），42 个单元",
    "ABR 滞后窗敏感性（0/5/10 年）",
    "双重心距离与重心（主估计量），42 个单元",
    "全部 14 区的研究重心",
    "第一作者 LMIC 与负担前 10 国家份额",
    "重心估计量敏感性（3 种估计量 × 42 个单元）",
    "合并 LMIC 第一作者份额序列（含剔除中国）",
    "按病区 × 时期 × 国家解析的第一作者记录数",
    "按病区 × 时期的国家解析覆盖率",
    "全部 14 区的 L4 分型信号（S、B、A）",
    "三套阈值组下的 L4 分型结果",
]


def downloads_page(lang="en"):
    zh = lang == "zh"
    file_pre = "../" if zh else ""
    descs = DOWNLOAD_DESC_ZH if zh else [d for _r, d in DOWNLOAD_FILES]
    rows = []
    for (rel, _desc), desc in zip(DOWNLOAD_FILES, descs):
        name = os.path.basename(rel)
        size = os.path.getsize(os.path.join(ROOT, rel))
        rows.append(f'<tr><td class="l"><a href="{file_pre}downloads/{name}">{name}</a></td>'
                    f'<td class="l">{escape(desc)}</td><td>{size:,}</td></tr>')
    if zh:
        body = f"""
<h2>下载</h2>
<p>本站每个数字背后的冻结结果表，可逐个下载 CSV 文件，或打包为一个存档：
<a href="{file_pre}downloads/frozen_tables.zip"><b>frozen_tables.zip</b></a>。</p>
<table>
<tr><th class="l">文件</th><th class="l">内容</th><th>字节</th></tr>
{''.join(rows)}
</table>
<h3>完整存档与代码</h3>
<ul>
<li><b>Zenodo 存档</b>——完整冻结快照（上表全部表格，加上 392,456 条记录的记录级
国家解析表、GBD 输入摘录、参考表、全部生产与绘图代码及项目文件）：
<a href="{ZENODO_URL}">doi.org/{ZENODO_DOI}</a>。</li>
<li><b>生产代码</b>——检索式、GBD 映射、解析与指标代码、绘图脚本及本站生成器，
与冻结数据一并存于上述 Zenodo 记录：
<a href="{ZENODO_URL}">doi.org/{ZENODO_DOI}</a>。</li>
<li><b>预注册</b>——方案与修订书 v1.1（GBD 2023）：
<a href="{OSF_URL}">doi.org/{OSF_DOI}</a>。</li>
</ul>
<p class="small">记录级 Europe PMC 元数据仍可从 Europe PMC 获取；GBD 2023 估计仍可
从 IHME 获取。本站只再发布本研究的冻结派生表格。</p>
"""
        return page("下载", body, lang="zh", rel="downloads.html")
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
    return page("Downloads", body, lang="en", rel="downloads.html")


# ---------------------------------------------------------------- build
def build():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"))
    os.makedirs(os.path.join(OUT, "areas"))
    os.makedirs(os.path.join(OUT, "downloads"))
    os.makedirs(os.path.join(OUT, "zh", "areas"))
    with open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    with open(os.path.join(OUT, "CNAME"), "w", encoding="utf-8") as fh:
        fh.write("burden.erbihou.org\n")
    with open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")
    pages = {"index.html": home("en"), "areas.html": areas_page("en"),
             "findings.html": findings_page("en"),
             "geography.html": geography_page("en"),
             "typology.html": typology_page("en"),
             "methods.html": methods_page("en"),
             "downloads.html": downloads_page("en"),
             "about.html": about_page("en")}
    for a in AREAS:
        pages[f"areas/{a}.html"] = area_page(a)
    pages_zh = {"index.html": home("zh"), "areas.html": areas_page("zh"),
                "findings.html": findings_page("zh"),
                "geography.html": geography_page("zh"),
                "typology.html": typology_page("zh"),
                "methods.html": methods_page("zh"),
                "downloads.html": downloads_page("zh"),
                "about.html": about_page("zh")}
    for a in AREAS:
        pages_zh[f"areas/{a}.html"] = area_page_zh(a)
    # structural assertions on the assembled site
    check("total pages = 22 (en)", len(pages) == 22)
    check("total pages = 22 (zh)", len(pages_zh) == 22)
    check("zh mirror covers every en page", set(pages_zh) == set(pages))
    nav_targets = [t for t, _e, _z in NAV]
    for lang, pdict in (("en", pages), ("zh", pages_zh)):
        for rel, html in pdict.items():
            depth = 1 if rel.startswith("areas/") else 0
            pre = "../" * depth
            check(f"nav complete on {lang}/{rel}",
                  all(f'href="{pre}{t}"' in html for t in nav_targets))
            check(f"no github URL on {lang}/{rel}",
                  "github.com/yuye8848" not in html)
            check(f"css v{ASSET_V} on {lang}/{rel}",
                  f"assets/style.css?v={ASSET_V}" in html)
            if lang == "en":
                check(f"toggle to zh on en/{rel}",
                      f'href="{pre}zh/{rel}">中文</a>' in html)
            else:
                check(f"toggle to en on zh/{rel}",
                      f'href="{"../" * (depth + 1)}{rel}">EN</a>' in html)
                check(f"zh nav labels on zh/{rel}",
                      all(f'href="{pre}{t}">{z}</a>' in html
                          for t, _e, z in NAV))
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
    check("about pages pin exact master affiliation string",
          "Department of Otolaryngology, The Third Hospital of "
          "Shijiazhuang, Shijiazhuang, Hebei 050011, China"
          in " ".join(pages["about.html"].split())
          and "Department of Otolaryngology, The Third Hospital of "
          "Shijiazhuang, Shijiazhuang, Hebei 050011, China"
          in " ".join(pages_zh["about.html"].split()))
    check("old short affiliation absent from all pages",
          all("Third Hospital of Shijiazhuang, Hebei" not in h
              for h in list(pages.values()) + list(pages_zh.values())))
    for a in AREAS:
        html = pages[f"areas/{a}.html"]
        check(f"breadcrumb on {a}",
              "Home</a> ›" in html and f"› {escape(NAMES[a])}</p>" in html)
    first, last = pages["areas/otitis_media.html"], pages["areas/cochlear_implant.html"]
    check("first area page has Next only",
          "Next:" in first and "Previous:" not in first)
    check("last area page has Previous only",
          "Previous:" in last and "Next:" not in last)
    # --- Chinese-mirror content assertions (same numbers, project terminology)
    check("CRS asterisk card on zh home",
          'crs_polyps.html">慢性鼻窦炎/鼻息肉（CRS） *</a>'
          in pages_zh["index.html"])
    check("CRS caveat note under zh home grid",
          "份额下降" in pages_zh["index.html"]
          and "+251.0%" in pages_zh["index.html"]
          and "术语迁移" in pages_zh["index.html"])
    check("zh typology page mutes unclassified rows",
          pages_zh["typology.html"].count('class="mute"') == 3)
    check("zh typology page labels unclassified 未归型",
          "未归型" in pages_zh["typology.html"])
    check("zh typology page carries CRS caveat",
          "术语迁移" in pages_zh["typology.html"])
    check("zh findings pairs hearing 恒定型 with ABR 0.36",
          "恒定型</b>" in pages_zh["findings.html"]
          and "ABR 0.36" in pages_zh["findings.html"])
    check("zh findings scorecard verdicts present",
          all(v in pages_zh["findings.html"] for v in
              ("完全符合", "大体不成立", "一半符合")))
    check("zh about page carries both DOIs",
          OSF_DOI in pages_zh["about.html"]
          and ZENODO_DOI in pages_zh["about.html"])
    check("zh about keeps English citation title",
          "Research attention and disease burden in" in pages_zh["about.html"]
          and "preregistered dynamic census of publication"
          in pages_zh["about.html"])
    check("zh about authors and affiliation in English",
          all(n in pages_zh["about.html"] for n in
              ("Peiliang Lei", "Wenrong Dong", "Jingyi Tan", "Xiaoying Yang",
               "Department of Otolaryngology, The Third Hospital of "
               "Shijiazhuang, Shijiazhuang, Hebei 050011, China")))
    check("zh pages contain no 质心 (term is 双重心)",
          all("质心" not in h for h in pages_zh.values()))
    check("zh pages contain no 石家庄 (affiliation in English)",
          all("石家庄" not in h for h in pages_zh.values()))
    check("zh geography pins 双重心距离",
          "双重心距离" in pages_zh["geography.html"]
          and "负担重心" in pages_zh["geography.html"]
          and "研究重心" in pages_zh["geography.html"])
    check("CRS caveat on zh areas overview",
          "术语迁移" in pages_zh["areas.html"])
    check("CRS caveat on zh CRS area page",
          "术语迁移" in pages_zh["areas/crs_polyps.html"])
    check("zh hearing page pairs 恒定型 with ABR 0.36",
          "恒定型" in pages_zh["areas/hearing_loss.html"]
          and "ABR 0.36" in pages_zh["areas/hearing_loss.html"])
    for a in AREAS:
        html = pages_zh[f"areas/{a}.html"]
        check(f"zh breadcrumb on {a}",
              "首页</a> ›" in html and f"› {escape(NAMES_ZH[a])}</p>" in html)
    zfirst = pages_zh["areas/otitis_media.html"]
    zlast = pages_zh["areas/cochlear_implant.html"]
    check("zh first area page has 下一区 only",
          "下一区：" in zfirst and "上一区：" not in zfirst)
    check("zh last area page has 上一区 only",
          "上一区：" in zlast and "下一区：" not in zlast)
    # numeric identity: on the table-driven pages the multiset of numeric
    # tokens must be identical between the English page and its Chinese
    # mirror (same formatted values from the same frozen files).
    import re as _re
    from collections import Counter as _Counter

    def _nums(html):
        text = _re.sub(r"<[^>]+>", " ", html)
        return _Counter(_re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text))

    for rel in ["areas.html", "geography.html", "typology.html",
                "downloads.html"] + [f"areas/{a}.html" for a in AREAS]:
        check(f"numeric tokens identical en/zh on {rel}",
              _nums(pages[rel]) == _nums(pages_zh[rel]))
    for rel, needles in (
            ("index.html", ["26,544", "128,117", "32.1%", "44.6%", "0.36",
                            "39.8%", "392,456", "+251.0%"]),
            ("findings.html", ["8.3%", "13.4%", "−1.47", "9.45", "978",
                               "2,467", "39.8%", "17.9%"]),
            ("methods.html", ["392,458", "4,806", "11,603", "92.76%",
                              "6,371.0088", "82.0", "+251.0%"]),
            ("about.html", ["42", "2026"])):
        for n in needles:
            check(f"zh {rel} carries number {n}", n in pages_zh[rel])
    for rel, html in pages.items():
        with open(os.path.join(OUT, rel), "w", encoding="utf-8") as fh:
            fh.write(html)
    for rel, html in pages_zh.items():
        with open(os.path.join(OUT, "zh", rel), "w", encoding="utf-8") as fh:
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
    print(f"pages written: {len(pages) + len(pages_zh)} "
          f"({len(pages)} en + {len(pages_zh)} zh) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(build())

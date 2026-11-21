#!/usr/bin/env python3
"""Prepare the Zenodo staging tree for the ENT attention-burden census archive.

Copies the frozen data tables, production code, figure code and project
documents into site_build/zenodo_staging/ preserving relative paths (the
Zenodo helper flattens '/' to '__' at upload time), and writes
STRUCTURE_MAP.md mapping every flattened archive name back to its original
project path. Prints the file count and total bytes for verification.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STAGE = os.path.join(HERE, "zenodo_staging")

FILES = [
    # frozen data tables
    "data_l1/l1_counts_by_year.csv",
    "data_l1/l1_counts_backup_by_year.csv",
    "data_l1/terminology_sensitivity.csv",
    "data_l2/FREEZE.md",
    "data_l2/abr/FREEZE.md",
    "data_l2/abr/abr_primary.csv",
    "data_l2/abr/abr_prevalence_sensitivity.csv",
    "data_l2/abr/abr_sensitivity_pub2020_2023.csv",
    "data_l2/abr/abr_lag_sensitivity.csv",
    "data_l3/DISCREPANCIES.md",
    "data_l3/l3_pull_summary.csv",
    "data_l3/geo/FREEZE.md",
    "data_l3/geo/COUNTRY_PARSE_QA.md",
    "data_l3/geo/country_counts.csv",
    "data_l3/geo/parse_coverage.csv",
    "data_l3/geo/records_country.csv",
    "data_l3/geo/unparsed_top_tails.csv",
    "data_l3/geo/centroid/double_centroid.csv",
    "data_l3/geo/centroid/research_centroids_all14.csv",
    "data_l3/geo/centroid/author_shares.csv",
    "data_l3/geo/centroid/estimator_sensitivity.csv",
    "data_l3/geo/centroid/lmic_series_recomputed.csv",
    "data_l3/geo/centroid/FREEZE_v2.md",
    "data_l3/geo/centroid/ESTIMATOR_诊断_2026-11-12.md",
    "data_l3/geo/ref/country_reference.csv",
    "data_l3/geo/ref/gbd_location_iso_map.csv",
    "data_l3/geo/ref/countries_mledoze.json",
    "data_l3/geo/ref/worldbank_country_income.json",
    "data_l4/FREEZE.md",
    "data_l4/signals.csv",
    "data_l4/typology.csv",
    # project documents (protocol layer)
    "docs/工作报告_v1_签批版_2026-11-08.md",
    "docs/协议修订书_v1.1_GBD2023_2026-11-10.md",
    "docs/L4_分型规则表_2026-11-12.md",
    "docs/术语敏感性_备用检索式_冻结_2026-11-12.md",
    "docs/敏感性补做_冻结与裁定_2026-11-12.md",
    "docs/图谱站建站任务书_2026-11-12.md",
    # site generator (produces the atlas website from the same frozen files)
    "site_build/build_site.py",
]
DOC_SRC = {
    "docs/工作报告_v1_签批版_2026-11-08.md": "工作报告_v1_签批版_2026-11-08.md",
    "docs/协议修订书_v1.1_GBD2023_2026-11-10.md": "协议修订书_v1.1_GBD2023_2026-11-10.md",
    "docs/L4_分型规则表_2026-11-12.md": "L4_分型规则表_2026-11-12.md",
    "docs/术语敏感性_备用检索式_冻结_2026-11-12.md": "术语敏感性_备用检索式_冻结_2026-11-12.md",
    "docs/敏感性补做_冻结与裁定_2026-11-12.md": "敏感性补做_冻结与裁定_2026-11-12.md",
    "docs/图谱站建站任务书_2026-11-12.md": "图谱站建站任务书_2026-11-12.md",
}
RAW_GBD = "data_l2/raw"  # all GBD 2023 extract CSVs (14 files)


def main():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    staged = []  # (staging_rel, original_rel, bytes)
    for rel in FILES:
        src_rel = DOC_SRC.get(rel, rel)
        if rel == "site_build/build_site.py":
            src_rel = os.path.join("site_build", "build_site.py")
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(STAGE, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        staged.append((rel, src_rel, os.path.getsize(dst)))
    raw_dir = os.path.join(ROOT, RAW_GBD)
    for name in sorted(os.listdir(raw_dir)):
        if name.endswith(".csv"):
            rel = f"{RAW_GBD}/{name}"
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(raw_dir, name), dst)
            staged.append((rel, rel, os.path.getsize(dst)))
    scripts_dir = os.path.join(ROOT, "scripts")
    for name in sorted(os.listdir(scripts_dir)):
        if name.endswith(".py"):
            rel = f"scripts/{name}"
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(scripts_dir, name), dst)
            staged.append((rel, rel, os.path.getsize(dst)))
    fig_dir = os.path.join(ROOT, "figures", "scripts")
    for name in sorted(os.listdir(fig_dir)):
        if name.endswith(".R"):
            rel = f"figures/scripts/{name}"
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(fig_dir, name), dst)
            staged.append((rel, rel, os.path.getsize(dst)))

    readme = """# Frozen data and code — ENT attention–burden census, 1995–2024

This archive is the frozen snapshot behind the ENT Burden Atlas
(burden.erbihou.org) and the manuscript "Research attention and disease
burden in otolaryngology, 1995–2024: a preregistered dynamic census"
(in preparation).

Contents: frozen derived tables for the four analysis layers (publication
shares, attention–burden ratios, geographic double-centroid distances and
author shares, decoupling typology), the record-level country-parse table
for 392,456 Europe PMC records, the GBD 2023 input extracts used, the
geographic reference tables, all production and figure code, the atlas
site generator, and the protocol-layer documents (signed work report,
Amendment v1.1, typology rule table, terminology-sensitivity freeze and
verdict; several documents are in Chinese, as produced).

Filenames in this record are flattened: each '/' of the original project
path is replaced by '__'. STRUCTURE_MAP.md gives the original path of
every file.

Reading rules that travel with the data: "resolution"/burden decline
always denotes relative share dilution inside the defined pools (absolute
DALYs rose for all seven burden-tier causes); the CRS/polyps share decline
is subject to a terminology-migration caveat (see
data_l1__terminology_sensitivity.csv and the sensitivity verdict
document); hearing loss's "constant" typology label describes dynamics
only and must be read with its level, ABR 0.36 in 2020–24.
Preregistration: OSF, DOI 10.17605/OSF.IO/NUC4B.
"""
    with open(os.path.join(STAGE, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)
    staged.append(("README.md", "(archive readme, written for this deposit)",
                   os.path.getsize(os.path.join(STAGE, "README.md"))))

    lines = ["# Structure map — flattened archive name → original project path",
             "",
             "Zenodo filenames replace each '/' of the original path with '__'.",
             ""]
    total = 0
    for rel, orig, size in staged:
        flat = rel.replace("/", "__")
        lines.append(f"- `{flat}` → `{orig}` ({size:,} bytes)")
        total += size
    lines.append("")
    lines.append(f"Files listed: {len(staged)} (plus this STRUCTURE_MAP.md). "
                 f"Total bytes of listed files: {total:,}.")
    with open(os.path.join(STAGE, "STRUCTURE_MAP.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    total += os.path.getsize(os.path.join(STAGE, "STRUCTURE_MAP.md"))
    print(f"staged files (incl. STRUCTURE_MAP.md): {len(staged) + 1}")
    print(f"total bytes: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

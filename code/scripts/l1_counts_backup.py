#!/usr/bin/env python3
"""
Terminology-drift sensitivity counts: backup queries frozen in
术语敏感性_备用检索式_冻结_2026-11-12.md (written 2026-11-12, before any
backup count was retrieved). Counting mirrors scripts/l1_counts.py exactly
(Europe PMC hitCount, TITLE_ABS, PUB_YEAR, 1995-2024) so that the only
difference from the primary L1 table is the query wording.

Output: data_l1/l1_counts_backup_by_year.csv (+ sha256 printed).
"""
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
AREAS_BACKUP = {
    "otitis_media": 'TITLE_ABS:("otitis media" OR "middle ear infection" OR "middle ear infections")',
    "hearing_loss": 'TITLE_ABS:("hearing loss" OR "sensorineural hearing" OR hypoacusis OR "auditory impairment")',
    "larynx_cancer": 'TITLE_ABS:("laryngeal neoplasm" OR "laryngeal neoplasms" OR "cancer of larynx")',
    "oral_cancer": 'TITLE_ABS:("oral neoplasm" OR "oral neoplasms" OR "mouth neoplasm" OR "oral cavity carcinoma" OR OSCC)',
    "nasopharynx_cancer": 'TITLE_ABS:("nasopharyngeal carcinoma" OR "nasopharynx cancer" OR "nasopharyngeal cancer")',
    "other_pharynx_cancer": 'TITLE_ABS:("oropharyngeal cancer" OR "oropharyngeal carcinoma" OR "hypopharyngeal cancer" OR "hypopharyngeal carcinoma" OR OPSCC)',
    "thyroid_cancer": 'TITLE_ABS:("thyroid neoplasm" OR "thyroid neoplasms" OR "thyroid malignancy" OR "papillary thyroid")',
    "crs_polyps": 'TITLE_ABS:("chronic rhinosinusitis" OR CRSwNP OR CRSsNP OR "nasal polyposis")',
    "allergic_rhinitis": 'TITLE_ABS:("allergic rhinitis" OR "hay fever" OR "allergic rhinoconjunctivitis")',
    "osa": 'TITLE_ABS:("sleep apnoea syndrome" OR "sleep apnea syndrome" OR OSAHS OR "obstructive sleep apnoea" OR "obstructive sleep apnea")',
    "tinnitus": 'TITLE_ABS:(tinnitus OR "phantom auditory")',
    "vertigo": 'TITLE_ABS:(vertigo OR "Meniere disease" OR BPPV OR "vestibular disorder" OR "vestibular disorders")',
    "cholesteatoma": 'TITLE_ABS:(cholesteatoma OR cholesteatomas OR "middle ear cholesteatoma")',
    "cochlear_implant": 'TITLE_ABS:("cochlear implant" OR "cochlear implantation" OR "auditory prosthesis" OR "cochlear prosthesis")',
}


def count(q, year):
    query = f"{q} AND PUB_YEAR:{year}"
    url = BASE + "?" + urllib.parse.urlencode(
        {"query": query, "format": "json", "pageSize": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "muse-l1-backup/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["hitCount"]
        except Exception:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed {query}")


rows = []
for area, q in AREAS_BACKUP.items():
    for y in range(1995, 2025):
        rows.append({"area": area, "year": y, "count": count(q, y)})
        time.sleep(0.15)
    print("done", area, flush=True)

with open("data_l1/l1_counts_backup_by_year.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["area", "year", "count"])
    w.writeheader()
    w.writerows(rows)
h = hashlib.sha256(open("data_l1/l1_counts_backup_by_year.csv", "rb").read()).hexdigest()
print("rows:", len(rows), "sha256:", h)

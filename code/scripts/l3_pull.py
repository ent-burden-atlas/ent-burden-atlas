#!/usr/bin/env python3
"""L3 record-level pull for ENT attention-burden census (signed work report v1, step 2).

Pulls Europe PMC core records for each frozen area x 5-year period, keeping the
fields needed for first-author affiliation / geography parsing:
  pmid, doi, pub_year, title, first_author, first_author_affiliation,
  any_affiliation (first affiliation string found on any author, fallback),
  has_first_affiliation (0/1)

Design rules (from 工作报告_v1_签批版_2026-11-08.md §4 L3 + §7 step 2):
- Search strings are FROZEN: copied verbatim from scripts/l1_counts.py.
  Any change requires a protocol amendment, not an edit here.
- Checkpointing: one JSONL part per (area, period) under data_l3/parts/,
  plus a <part>.done marker storing the Europe PMC hitCount at completion.
  A part is skipped only when its .done marker exists AND its stored
  hitCount still equals the live hitCount AND its line count equals it.
- Missing affiliations are reported, never imputed (completeness CSV).
- Raw pull only: country parsing is a separate later step (institution
  dictionary), so this script stores affiliation text verbatim.

Usage:
  python3 scripts/l3_pull.py                      # all areas, all periods
  python3 scripts/l3_pull.py --areas cholesteatoma --periods 1995-1999
Run from the project root (~/workspace/ent-attention-burden/).
"""
import argparse, csv, hashlib, json, os, sys, time
import urllib.request, urllib.parse

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PAGE_SIZE = 1000
PARTS_DIR = "data_l3/parts"
SUMMARY_CSV = "data_l3/l3_pull_summary.csv"

# FROZEN — verbatim copy of AREAS in scripts/l1_counts.py (checked 2026-11-09).
AREAS = {
 "otitis_media": 'TITLE_ABS:("otitis media")',
 "hearing_loss": 'TITLE_ABS:("hearing loss" OR "hearing impairment" OR deafness OR presbycusis)',
 "larynx_cancer": 'TITLE_ABS:("laryngeal cancer" OR "larynx cancer" OR "laryngeal carcinoma")',
 "oral_cancer": 'TITLE_ABS:("oral cancer" OR "oral cavity cancer" OR "mouth cancer" OR "oral squamous")',
 "nasopharynx_cancer": 'TITLE_ABS:(nasopharyngeal)',
 "other_pharynx_cancer": 'TITLE_ABS:(oropharyngeal OR hypopharyngeal OR "oropharynx cancer" OR "hypopharynx cancer")',
 "thyroid_cancer": 'TITLE_ABS:("thyroid cancer" OR "thyroid carcinoma")',
 "crs_polyps": 'TITLE_ABS:(rhinosinusitis OR "chronic sinusitis" OR "nasal polyp" OR "nasal polyps" OR "sinusitis")',
 "allergic_rhinitis": 'TITLE_ABS:("allergic rhinitis")',
 "osa": 'TITLE_ABS:("sleep apnea" OR "sleep apnoea" OR "obstructive sleep")',
 "tinnitus": 'TITLE_ABS:(tinnitus)',
 "vertigo": 'TITLE_ABS:(vertigo OR meniere OR "benign paroxysmal positional")',
 "cholesteatoma": 'TITLE_ABS:(cholesteatoma)',
 "cochlear_implant": 'TITLE_ABS:("cochlear implant" OR "cochlear implants" OR "cochlear implantation")',
}
PERIODS = [(1995, 1999), (2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024)]

def fetch(params, tries=4):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "muse-l3/1.0"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))

def hit_count(query):
    return fetch({"query": query, "format": "json", "pageSize": 1})["hitCount"]

def author_aff(a):
    # Europe PMC core: per-author affiliations live in
    # authorAffiliationDetailsList.authorAffiliation[].affiliation
    # (verified live 2026-11-09; there is no author-level "affiliation" key).
    details = (a.get("authorAffiliationDetailsList") or {}).get("authorAffiliation") or []
    for d in details:
        if d.get("affiliation"):
            return d["affiliation"]
    return ""

def extract(rec):
    authors = (rec.get("authorList") or {}).get("author") or []
    first = authors[0] if authors else {}
    first_aff = author_aff(first)
    any_aff = ""
    for a in authors:
        any_aff = author_aff(a)
        if any_aff:
            break
    if not any_aff:
        any_aff = rec.get("affiliation") or ""  # record-level fallback field
    return {
        "epmc_id": rec.get("id", ""),
        "pmid": rec.get("pmid", ""),
        "doi": rec.get("doi", ""),
        "pub_year": rec.get("pubYear", ""),
        "title": (rec.get("title") or "").replace("\n", " "),
        "first_author": first.get("fullName", ""),
        "first_author_affiliation": first_aff.replace("\n", " "),
        "any_affiliation": any_aff.replace("\n", " "),
        "has_first_affiliation": 1 if first_aff else 0,
    }

# DOCUMENTED EXCEPTIONS (user ruling 2026-11-09: write the discrepancy into
# the record and proceed with the retrievable set). (area, y0, y1) ->
# (live hitCount, retrievable unique records). Evidence for the one entry:
# Europe PMC counts a record it never serves — core and lite pagination
# return identical ID sets of 4805 against a hitCount of 4806 (verified by
# direct re-query three times on 2026-11-09); isolated to year 2014
# (counted 1142 vs 1141 retrievable). The .done meta of such a part stores
# both numbers and an "exception" note.
EXCEPTIONS = {("oral_cancer", 2010, 2014): (4806, 4805)}

# GENERAL RULE (user ruling 2026-11-09 13:20, after D-1): any later part
# whose retrievable set is exactly hitCount - 1 is handled the same way
# AUTOMATICALLY — no stop, no per-part ruling — but only after the phantom
# pattern is verified in-code (all three checks must pass):
#   (1) every retrieved record has a unique, non-empty Europe PMC id
#       (nothing was lost to pagination duplication);
#   (2) a fresh hitCount re-query is unchanged (the index is stable);
#   (3) an independent lite-mode pagination returns exactly the same
#       id set as the core pull (two channels agree on what exists).
# Any other mismatch (difference != 1, or any check fails) still raises
# and stops for a user ruling. Each auto-accepted part records the
# exception in its .done meta and must be logged in
# data_l3/DISCREPANCIES.md by the supervising agent.
def lite_id_set(query):
    ids, cursor = set(), "*"
    while True:
        resp = fetch({"query": query, "format": "json", "resultType": "lite",
                      "pageSize": PAGE_SIZE, "cursorMark": cursor})
        results = resp.get("resultList", {}).get("result", [])
        ids.update(r.get("id", "") for r in results)
        nxt = resp.get("nextCursorMark")
        if not results or not nxt or nxt == cursor:
            break
        cursor = nxt
        time.sleep(0.2)
    return ids

def verify_phantom(query, rows, expected):
    if len(rows) != expected - 1:
        return False
    core_ids = [r["epmc_id"] for r in rows]
    if not all(core_ids) or len(set(core_ids)) != len(core_ids):
        return False
    if hit_count(query) != expected:
        return False
    return lite_id_set(query) == set(core_ids)

def pull_part(area, y0, y1):
    query = f"{AREAS[area]} AND PUB_YEAR:[{y0} TO {y1}]"
    part = os.path.join(PARTS_DIR, f"{area}_{y0}-{y1}.jsonl")
    done = part + ".done"
    expected = hit_count(query)
    if os.path.exists(done) and os.path.exists(part):
        try:
            meta = json.load(open(done))
            n_lines = sum(1 for _ in open(part))
            exc = EXCEPTIONS.get((area, y0, y1))
            target = exc[1] if exc and exc[0] == expected else expected
            if meta.get("hit_count") == expected and meta.get("retrievable"):
                target = meta["retrievable"]
            if meta.get("hit_count") == expected and n_lines == target:
                print(f"skip {area} {y0}-{y1}: done, {expected} records", flush=True)
                return {"area": area, "period": f"{y0}-{y1}", "hit_count": expected,
                        "pulled": n_lines, "with_first_affiliation": meta.get("with_first_affiliation", "")}
        except Exception:
            pass  # fall through and re-pull
    rows, cursor = [], "*"
    while True:
        resp = fetch({"query": query, "format": "json", "resultType": "core",
                      "pageSize": PAGE_SIZE, "cursorMark": cursor})
        results = resp.get("resultList", {}).get("result", [])
        rows.extend(extract(r) for r in results)
        nxt = resp.get("nextCursorMark")
        if not results or not nxt or nxt == cursor:
            break
        cursor = nxt
        time.sleep(0.2)
    exc = EXCEPTIONS.get((area, y0, y1))
    auto_exc = False
    if len(rows) != expected and not (exc and exc[0] == expected and len(rows) == exc[1]):
        if verify_phantom(query, rows, expected):
            auto_exc = True
        else:
            raise RuntimeError(f"{area} {y0}-{y1}: pulled {len(rows)} != hitCount {expected}; part NOT marked done")
    with open(part, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with_aff = sum(r["has_first_affiliation"] for r in rows)
    meta_out = {"hit_count": expected, "with_first_affiliation": with_aff,
                "sha256": hashlib.sha256(open(part, "rb").read()).hexdigest()}
    if exc and len(rows) != expected:
        meta_out["retrievable"] = len(rows)
        meta_out["exception"] = ("hitCount exceeds retrievable unique records by 1 "
                                 "(documented phantom; user ruling 2026-11-09)")
    if auto_exc:
        meta_out["retrievable"] = len(rows)
        meta_out["exception"] = ("hitCount exceeds retrievable unique records by 1 "
                                 "(phantom verified in-code: unique ids, stable hitCount, "
                                 "core/lite id sets identical; general rule, user ruling "
                                 "2026-11-09 13:20)")
    json.dump(meta_out, open(done, "w"))
    print(f"done {area} {y0}-{y1}: {len(rows)} records, first-affiliation {with_aff} "
          f"({100.0*with_aff/max(len(rows),1):.1f}%)"
          + (f" [exception: hitCount {expected}]" if "exception" in meta_out else ""), flush=True)
    return {"area": area, "period": f"{y0}-{y1}", "hit_count": expected,
            "pulled": len(rows), "with_first_affiliation": with_aff}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--areas", default="")
    ap.add_argument("--periods", default="", help="e.g. 1995-1999,2020-2024")
    args = ap.parse_args()
    areas = args.areas.split(",") if args.areas else list(AREAS)
    periods = PERIODS
    if args.periods:
        want = set(args.periods.split(","))
        periods = [p for p in PERIODS if f"{p[0]}-{p[1]}" in want]
    bad = [a for a in areas if a not in AREAS]
    if bad:
        sys.exit(f"unknown areas: {bad}")
    os.makedirs(PARTS_DIR, exist_ok=True)
    summary = []
    for area in areas:
        for (y0, y1) in periods:
            summary.append(pull_part(area, y0, y1))
    os.makedirs(os.path.dirname(SUMMARY_CSV), exist_ok=True)
    write_header = not os.path.exists(SUMMARY_CSV)
    with open(SUMMARY_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["area", "period", "hit_count", "pulled", "with_first_affiliation"])
        if write_header:
            w.writeheader()
        w.writerows(summary)
    print("parts complete:", len(summary))

if __name__ == "__main__":
    main()

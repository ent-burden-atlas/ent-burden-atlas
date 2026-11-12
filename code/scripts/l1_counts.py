import urllib.request, urllib.parse, json, time, csv, hashlib, sys
BASE="https://www.ebi.ac.uk/europepmc/webservices/rest/search"
AREAS = {
 # burden tier (GBD-matched)
 "otitis_media": 'TITLE_ABS:("otitis media")',
 "hearing_loss": 'TITLE_ABS:("hearing loss" OR "hearing impairment" OR deafness OR presbycusis)',
 "larynx_cancer": 'TITLE_ABS:("laryngeal cancer" OR "larynx cancer" OR "laryngeal carcinoma")',
 "oral_cancer": 'TITLE_ABS:("oral cancer" OR "oral cavity cancer" OR "mouth cancer" OR "oral squamous")',
 "nasopharynx_cancer": 'TITLE_ABS:(nasopharyngeal)',
 "other_pharynx_cancer": 'TITLE_ABS:(oropharyngeal OR hypopharyngeal OR "oropharynx cancer" OR "hypopharynx cancer")',
 "thyroid_cancer": 'TITLE_ABS:("thyroid cancer" OR "thyroid carcinoma")',
 # attention tier
 "crs_polyps": 'TITLE_ABS:(rhinosinusitis OR "chronic sinusitis" OR "nasal polyp" OR "nasal polyps" OR "sinusitis")',
 "allergic_rhinitis": 'TITLE_ABS:("allergic rhinitis")',
 "osa": 'TITLE_ABS:("sleep apnea" OR "sleep apnoea" OR "obstructive sleep")',
 "tinnitus": 'TITLE_ABS:(tinnitus)',
 "vertigo": 'TITLE_ABS:(vertigo OR meniere OR "benign paroxysmal positional")',
 "cholesteatoma": 'TITLE_ABS:(cholesteatoma)',
 "cochlear_implant": 'TITLE_ABS:("cochlear implant" OR "cochlear implants" OR "cochlear implantation")',
}
def count(q, year):
    query=f'{q} AND PUB_YEAR:{year}'
    url=BASE+"?"+urllib.parse.urlencode({"query":query,"format":"json","pageSize":1})
    req=urllib.request.Request(url, headers={"User-Agent":"muse-l1/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)["hitCount"]
        except Exception as e:
            time.sleep(2*(attempt+1))
    raise RuntimeError(f"failed {query}")
rows=[]
for area,q in AREAS.items():
    for y in range(1995,2025):
        rows.append({"area":area,"year":y,"count":count(q,y)})
        time.sleep(0.15)
    print("done", area, flush=True)
with open("data_l1/l1_counts_by_year.csv","w",newline="") as f:
    w=csv.DictWriter(f, fieldnames=["area","year","count"]); w.writeheader(); w.writerows(rows)
h=hashlib.sha256(open("data_l1/l1_counts_by_year.csv","rb").read()).hexdigest()
print("rows:", len(rows), "sha256:", h)

#!/usr/bin/env python3
"""Pilot v2: layered scan parser. Rightmost country evidence in the whole
affiliation string wins: country names/variants, ISO-3 codes, US states,
Canadian provinces, and a top-city gazetteer. Emails stripped first."""
import json, re
from collections import Counter
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("p1", Path(__file__).parent / "l3_country_pilot.py")
p1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p1)

ISO3 = {"usa":"USA","chn":"China","jpn":"Japan","kor":"South Korea","ind":"India",
"deu":"Germany","fra":"France","ita":"Italy","esp":"Spain","gbr":"United Kingdom",
"can":"Canada","aus":"Australia","nld":"Netherlands","tur":"Turkey","bra":"Brazil",
"irn":"Iran","pol":"Poland","swe":"Sweden","bel":"Belgium","isr":"Israel",
"che":"Switzerland","grc":"Greece","fin":"Finland","dnk":"Denmark","sau":"Saudi Arabia",
"pak":"Pakistan","mys":"Malaysia","prt":"Portugal","mex":"Mexico","arg":"Argentina",
"chl":"Chile","zaf":"South Africa","egy":"Egypt","tha":"Thailand","idn":"Indonesia",
"phl":"Philippines","vnm":"Vietnam","rus":"Russia","ukr":"Ukraine","cze":"Czech Republic",
"hun":"Hungary","rou":"Romania","bgr":"Bulgaria","hrv":"Croatia","srb":"Serbia",
"svn":"Slovenia","svk":"Slovakia","ltu":"Lithuania","lva":"Latvia","est":"Estonia",
"isl":"Iceland","lux":"Luxembourg","col":"Colombia","per":"Peru","ven":"Venezuela",
"nga":"Nigeria","ken":"Kenya","eth":"Ethiopia","mar":"Morocco","tun":"Tunisia",
"dza":"Algeria","irq":"Iraq","jor":"Jordan","lbn":"Lebanon","are":"United Arab Emirates",
"qat":"Qatar","kwt":"Kuwait","omn":"Oman","yem":"Yemen","lka":"Sri Lanka",
"npl":"Nepal","mmr":"Myanmar","khm":"Cambodia","mng":"Mongolia","kaz":"Kazakhstan",
"uzb":"Uzbekistan","geo":"Georgia","arm":"Armenia","aze":"Azerbaijan","cyp":"Cyprus",
"mlt":"Malta","ury":"Uruguay","ecu":"Ecuador","bol":"Bolivia","cub":"Cuba",
"jam":"Jamaica","gha":"Ghana","tza":"Tanzania","uga":"Uganda","zwe":"Zimbabwe",
"sdn":"Sudan","lby":"Libya","syr":"Syria","afg":"Afghanistan","bih":"Bosnia and Herzegovina",
"mkd":"North Macedonia","alb":"Albania","mne":"Montenegro","mda":"Moldova",
"blr":"Belarus","kgz":"Kyrgyzstan","tjk":"Tajikistan","sgp":"Singapore",
"nzl":"New Zealand","irl":"Ireland","nor":"Norway","aut":"Austria","twn":"China",
"hkg":"China","prk":"North Korea"}
CITIES = {"beijing":"China","shanghai":"China","guangzhou":"China","wuhan":"China",
"changsha":"China","taipei":"China","tokyo":"Japan","seoul":"South Korea",
"london":"United Kingdom","paris":"France","madrid":"Spain","barcelona":"Spain",
"valencia":"Spain","roma":"Italy","rome":"Italy","milan":"Italy","torino":"Italy",
"ann arbor":"USA","ontario":"Canada","quebec":"Canada","québec":"Canada",
"british columbia":"Canada","alberta":"Canada","méxico":"Mexico","mexico city":"Mexico",
"tunisie":"Tunisia","maroc":"Morocco","belgique":"Belgium","karnataka":"India",
"new delhi":"India","mumbai":"India","istanbul":"Turkey","ankara":"Turkey",
"tehran":"Iran","cairo":"Egypt","riyadh":"Saudi Arabia","são paulo":"Brazil",
"sao paulo":"Brazil","warsaw":"Poland","athens":"Greece","lisbon":"Portugal",
"vienna":"Austria","zurich":"Switzerland","berlin":"Germany","munich":"Germany",
"amsterdam":"Netherlands","stockholm":"Sweden","copenhagen":"Denmark",
"helsinki":"Finland","oslo":"Norway","dublin":"Ireland","auckland":"New Zealand",
"sydney":"Australia","melbourne":"Australia","bangkok":"Thailand",
"kuala lumpur":"Malaysia","jakarta":"Indonesia","manila":"Philippines",
"hanoi":"Vietnam","karachi":"Pakistan","dhaka":"Bangladesh","moscow":"Russia",
"kyiv":"Ukraine","prague":"Czech Republic","budapest":"Hungary",
"bucharest":"Romania","sofia":"Bulgaria","zagreb":"Croatia","belgrade":"Serbia",
"kingdom of saudi arabia":"Saudi Arabia","china (mainland)":"China",
"p. r. china":"China","p.r. china":"China","ir iran":"Iran"}

PATTERNS = []
for canon, variants in p1.COUNTRIES.items():
    for v in variants:
        PATTERNS.append((v, canon))
for code, canon in ISO3.items():
    PATTERNS.append((code, canon))
for st in p1.US_STATES:
    PATTERNS.append((st, "USA"))
for city, canon in CITIES.items():
    PATTERNS.append((city, canon))
# longest first so 'new york' beats 'york'-like fragments; compile one regex per pattern is slow,
# instead: tokenise string into segments and scan segment-wise rightmost-first.
SEG_LOOKUP = {}
for pat, canon in PATTERNS:
    SEG_LOOKUP[pat] = canon

EMAIL = re.compile(r"\S+@\S+")
def parse2(aff):
    s = EMAIL.sub(" ", aff.lower())
    s = s.replace(";", ",")
    segs = [re.sub(r"\s+", " ", x).strip(" .") for x in s.split(",")]
    segs = [x for x in segs if x]
    for seg in reversed(segs):
        if seg in SEG_LOOKUP:
            return SEG_LOOKUP[seg]
        # segment may end with the country token, e.g. 'karnataka india'
        for pat, canon in SEG_LOOKUP.items():
            if seg.endswith(" " + pat) or seg == pat:
                return canon
    return None

def main():
    from collections import Counter
    aff_counter = Counter(); total = with_aff = 0
    parts = p1.PARTS
    for f in sorted(parts.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                total += 1
                r = json.loads(line)
                aff = (r.get("first_author_affiliation") or "").strip()
                if aff:
                    with_aff += 1; aff_counter[aff] += 1
    matched = Counter(); unmatched_tail = Counter(); n_matched = 0
    for aff, n in aff_counter.items():
        c = parse2(aff)
        if c: matched[c] += n; n_matched += n
        else:
            segs = [re.sub(r"\s+"," ",x).strip(" .") for x in EMAIL.sub(" ", aff.lower()).split(",") if x.strip()]
            unmatched_tail[segs[-1] if segs else "(empty)"] += n
    out = []
    out.append("# L3 country-parsing pilot v2 — layered scan parser (NOT frozen production)")
    out.append("")
    out.append(f"- records total: {total}; with affiliation: {with_aff}")
    out.append(f"- matched: {n_matched} ({n_matched/with_aff:.2%} of with-affiliation)")
    out.append(f"- unmatched: {with_aff-n_matched} ({(with_aff-n_matched)/with_aff:.2%})")
    out.append("")
    out.append("## Top matched countries")
    for c, n in matched.most_common(20): out.append(f"- {c}: {n}")
    out.append("")
    out.append("## Top 30 unmatched tail segments")
    for t, n in unmatched_tail.most_common(30): out.append(f"- {t!r}: {n}")
    out.append("")
    out.append(f"Distinct unmatched tails: {len(unmatched_tail)}")
    p1.OUT.mkdir(exist_ok=True)
    (p1.OUT / "pilot2_summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))

if __name__ == "__main__":
    main()

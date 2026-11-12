#!/usr/bin/env python3
"""L3 country-parsing PILOT (not a frozen production run).

Reads all data_l3/parts/*.jsonl, tallies unique first-author affiliation
strings, and tests a tail-segment dictionary parser:
  - last comma segment (then second-to-last as fallback) matched against
    country names/variants and US state names.
Outputs coverage stats + the top unmatched tail segments (the worklist a
full production parser would need to resolve).
"""
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "data_l3" / "parts"
OUT = ROOT / "data_l3" / "country_pilot"
OUT.mkdir(exist_ok=True)

US_STATES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut",
    "delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa",
    "kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan",
    "minnesota","mississippi","missouri","montana","nebraska","nevada",
    "new hampshire","new jersey","new mexico","new york","north carolina",
    "north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island",
    "south carolina","south dakota","tennessee","texas","utah","vermont",
    "virginia","washington","west virginia","wisconsin","wyoming",
    "district of columbia","puerto rico",
    "al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in","ia",
    "ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv","nh","nj",
    "nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","vt",
    "va","wa","wv","wi","wy","dc",
}
# canonical -> variants (lowercase)
COUNTRIES = {
    "USA": ["usa","u.s.a","u.s","united states","united states of america","america"],
    "United Kingdom": ["uk","u.k","united kingdom","england","scotland","wales",
                       "northern ireland","great britain","britain"],
    "China": ["china","p.r. china","pr china","people's republic of china","hong kong","taiwan"],
    "Japan": ["japan"], "Germany": ["germany","deutschland"],
    "France": ["france"], "Italy": ["italy","italia"], "Spain": ["spain","españa","espana"],
    "Canada": ["canada"], "Australia": ["australia"], "Netherlands": ["netherlands","the netherlands","holland"],
    "South Korea": ["south korea","korea","republic of korea"],
    "India": ["india"], "Brazil": ["brazil","brasil"], "Switzerland": ["switzerland"],
    "Sweden": ["sweden"], "Belgium": ["belgium"], "Austria": ["austria"],
    "Denmark": ["denmark"], "Norway": ["norway"], "Finland": ["finland"],
    "Poland": ["poland"], "Turkey": ["turkey","türkiye","turkiye"],
    "Israel": ["israel"], "Greece": ["greece"], "Portugal": ["portugal"],
    "Ireland": ["ireland"], "New Zealand": ["new zealand"], "Singapore": ["singapore"],
    "Mexico": ["mexico"], "Argentina": ["argentina"], "Chile": ["chile"],
    "South Africa": ["south africa"], "Egypt": ["egypt"], "Iran": ["iran"],
    "Saudi Arabia": ["saudi arabia"], "Thailand": ["thailand"], "Malaysia": ["malaysia"],
    "Indonesia": ["indonesia"], "Philippines": ["philippines"], "Vietnam": ["vietnam","viet nam"],
    "Pakistan": ["pakistan"], "Bangladesh": ["bangladesh"], "Russia": ["russia","russian federation"],
    "Ukraine": ["ukraine"], "Czech Republic": ["czech republic","czechia"],
    "Hungary": ["hungary"], "Romania": ["romania"], "Bulgaria": ["bulgaria"],
    "Croatia": ["croatia"], "Serbia": ["serbia"], "Slovenia": ["slovenia"],
    "Slovakia": ["slovakia"], "Lithuania": ["lithuania"], "Latvia": ["latvia"],
    "Estonia": ["estonia"], "Iceland": ["iceland"], "Luxembourg": ["luxembourg"],
    "Colombia": ["colombia"], "Peru": ["peru"], "Venezuela": ["venezuela"],
    "Nigeria": ["nigeria"], "Kenya": ["kenya"], "Ethiopia": ["ethiopia"],
    "Morocco": ["morocco"], "Tunisia": ["tunisia"], "Algeria": ["algeria"],
    "Iraq": ["iraq"], "Jordan": ["jordan"], "Lebanon": ["lebanon"],
    "United Arab Emirates": ["united arab emirates","uae","u.a.e"],
    "Qatar": ["qatar"], "Kuwait": ["kuwait"], "Oman": ["oman"], "Yemen": ["yemen"],
    "Sri Lanka": ["sri lanka"], "Nepal": ["nepal"], "Myanmar": ["myanmar"],
    "Cambodia": ["cambodia"], "Mongolia": ["mongolia"], "Kazakhstan": ["kazakhstan"],
    "Uzbekistan": ["uzbekistan"], "Georgia": ["georgia"], "Armenia": ["armenia"],
    "Azerbaijan": ["azerbaijan"], "Cyprus": ["cyprus"], "Malta": ["malta"],
    "Uruguay": ["uruguay"], "Ecuador": ["ecuador"], "Bolivia": ["bolivia"],
    "Cuba": ["cuba"], "Jamaica": ["jamaica"], "Ghana": ["ghana"], "Tanzania": ["tanzania"],
    "Uganda": ["uganda"], "Zimbabwe": ["zimbabwe"], "Sudan": ["sudan"], "Libya": ["libya"],
    "Syria": ["syria","syrian arab republic"], "Afghanistan": ["afghanistan"],
    "Bosnia and Herzegovina": ["bosnia and herzegovina","bosnia"],
    "North Macedonia": ["north macedonia","macedonia"], "Albania": ["albania"],
    "Montenegro": ["montenegro"], "Moldova": ["moldova"], "Belarus": ["belarus"],
    "Kyrgyzstan": ["kyrgyzstan"], "Tajikistan": ["tajikistan"],
}
LOOKUP = {}
for canon, variants in COUNTRIES.items():
    for v in variants:
        LOOKUP[v] = canon

def clean(seg: str) -> str:
    s = seg.strip().strip(".").strip()
    s = re.sub(r"\s+", " ", s)
    # strip trailing postcode-like tokens
    s = re.sub(r"\s+\d{3,6}(-\d{4})?$", "", s)
    s = re.sub(r"\s+[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", "", s)  # UK-style postcode remnants
    return s.lower()

def parse(aff: str):
    if not aff:
        return None
    segs = [clean(s) for s in aff.split(",")]
    segs = [s for s in segs if s]
    for seg in reversed(segs[-2:]):
        if seg in LOOKUP:
            return LOOKUP[seg]
        if seg in US_STATES:
            return "USA"
    return None

def main():
    aff_counter = Counter()
    total = with_aff = 0
    for f in sorted(PARTS.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                total += 1
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                aff = (r.get("first_author_affiliation") or "").strip()
                if aff:
                    with_aff += 1
                    aff_counter[aff] += 1
    matched = Counter()
    unmatched_tail = Counter()
    n_matched = 0
    for aff, n in aff_counter.items():
        c = parse(aff)
        if c:
            matched[c] += n
            n_matched += n
        else:
            segs = [clean(s) for s in aff.split(",") if clean(s)]
            unmatched_tail[segs[-1] if segs else "(empty)"] += n
    n_unmatched = with_aff - n_matched
    lines = []
    lines.append("# L3 country-parsing pilot — coverage test (NOT frozen production)")
    lines.append("")
    lines.append(f"- records total: {total}")
    lines.append(f"- with first-author affiliation: {with_aff}")
    lines.append(f"- unique affiliation strings: {len(aff_counter)}")
    lines.append(f"- tail-dictionary matched: {n_matched} ({n_matched/with_aff:.2%} of with-affiliation)")
    lines.append(f"- unmatched: {n_unmatched} ({n_unmatched/with_aff:.2%})")
    lines.append("")
    lines.append("## Top matched countries (records)")
    for c, n in matched.most_common(25):
        lines.append(f"- {c}: {n}")
    lines.append("")
    lines.append("## Top 40 unmatched tail segments (records) — the manual worklist")
    for t, n in unmatched_tail.most_common(40):
        lines.append(f"- {t!r}: {n}")
    lines.append("")
    lines.append(f"Distinct unmatched tail segments: {len(unmatched_tail)}")
    (OUT / "pilot_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()

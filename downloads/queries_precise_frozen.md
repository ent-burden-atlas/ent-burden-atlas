# Precise query set — FROZEN (fix round Stage 1)

Frozen: 2026-11-21 (Europe PMC REST API hitCounts, TITLE_ABS + PUB_YEAR per year,
same counting method as scripts/l1_counts.py). All numbers below are generated
from candidates/candidate_yearly_counts.csv and the frozen L1 tables by
scripts/make_freeze_doc.py — none hand-transcribed.

**Unified principle (all five cancer areas):** site/anatomy concept AND a cancer
limiter, or cancer-specific phrases only. The shared limiter set is
C8 = (cancer OR carcinoma OR malignancy OR malignant OR neoplasm OR tumour OR tumor OR oncology).

## 1. nasopharynx_cancer — FREEZE: candidate C

- Original: `TITLE_ABS:(nasopharyngeal)` — total 1995–2024 40,188
- **Precise (frozen):** `TITLE_ABS:((nasopharyngeal OR nasopharynx) AND (cancer OR carcinoma OR malignancy OR malignant OR neoplasm OR tumour OR tumor OR oncology))` — total 22,115

Candidate comparison (2020–21 spike residue; original spike: 2019=1,720, 2020=3,540 (2.06×), 2021=4,725 (2.75×), 2020–21 sum=8,265):

| Candidate | Total 1995–2024 | 2020–24 | Spike residue |
|---|---|---|---|
| A: nasopharyngeal AND wildcard cancer words | 20,383 | 6,760 | 2019=1,093, 2020=1,348 (1.23×), 2021=1,468 (1.34×), 2020–21 sum=2,816 |
| B: cancer phrases only (= frozen backup query) | 17,750 | 5,917 | 2019=984, 2020=1,162 (1.18×), 2021=1,256 (1.28×), 2020–21 sum=2,418 |
| **C: (nasopharyngeal OR nasopharynx) AND C8 — FROZEN** | 22,115 | 7,166 | 2019=1,170, 2020=1,432 (1.22×), 2021=1,550 (1.32×), 2020–21 sum=2,982 |
| D: phrases + "nasopharynx carcinoma" | 17,801 | 5,924 | 2019=985, 2020=1,162 (1.18×), 2021=1,259 (1.28×), 2020–21 sum=2,421 |

Rationale: all four candidates abolish the spike (2021/2019 falls from 2.75× to
1.28–1.34×; the residue is in line with general pool growth). C is frozen because
it (i) applies the same C8 limiter set as the other-pharynx precise query
(cross-area consistency), (ii) covers both anatomy forms (nasopharyngeal /
nasopharynx), and (iii) has the highest recall among the principled candidates —
phrase-only forms (B/D) miss records where site and cancer words are
non-contiguous. Under C, the 2020–2024 count falls from 17,180 to
7,166 (−58%).

### Nasopharynx yearly counts, original vs precise (C)

| Year | Original | Precise C |
|---|---|---|
| 1995 | 371 | 221 |
| 1996 | 449 | 296 |
| 1997 | 443 | 289 |
| 1998 | 467 | 296 |
| 1999 | 472 | 297 |
| 2000 | 539 | 371 |
| 2001 | 580 | 380 |
| 2002 | 650 | 452 |
| 2003 | 649 | 423 |
| 2004 | 703 | 474 |
| 2005 | 731 | 491 |
| 2006 | 783 | 511 |
| 2007 | 802 | 509 |
| 2008 | 866 | 553 |
| 2009 | 871 | 558 |
| 2010 | 1,028 | 622 |
| 2011 | 1,102 | 621 |
| 2012 | 1,184 | 759 |
| 2013 | 1,232 | 799 |
| 2014 | 1,372 | 892 |
| 2015 | 1,456 | 983 |
| 2016 | 1,454 | 970 |
| 2017 | 1,525 | 985 |
| 2018 | 1,559 | 1,027 |
| 2019 | 1,720 | 1,170 |
| 2020 | 3,540 | 1,432 |
| 2021 | 4,725 | 1,550 |
| 2022 | 3,595 | 1,430 |
| 2023 | 2,834 | 1,356 |
| 2024 | 2,486 | 1,398 |
| **Total** | **40,188** | **22,115** |

## 2. other_pharynx_cancer — FREEZE: candidate A

- Original: `TITLE_ABS:(oropharyngeal OR hypopharyngeal OR "oropharynx cancer" OR "hypopharynx cancer")` — total 27,763
- **Precise (frozen):** `TITLE_ABS:((oropharyngeal OR hypopharyngeal OR oropharynx OR hypopharynx) AND (cancer OR carcinoma OR malignancy OR malignant OR neoplasm OR tumour OR tumor OR oncology))` — total 17,592

| Candidate | Total 1995–2024 | 2020–24 | Pattern |
|---|---|---|---|
| A: anatomy AND C8 — FROZEN | 17,592 | 6,135 | 2019=1,017, 2020=1,204 (1.18×), 2021=1,392 (1.37×), 2020–21 sum=2,596 |
| B: cancer phrases + OPSCC only | 8,377 | 3,452 | 2019=539, 2020=670 (1.24×), 2021=783 (1.45×), 2020–21 sum=1,453 |

Rationale: original also carried a milder 2020–21 bump (2019=1,447, 2020=2,070 (1.43×), 2021=2,418 (1.67×), 2020–21 sum=4,488). B is
rejected: phrase-only misses non-contiguous forms (e.g. "hypopharyngeal squamous
cell carcinoma" word order, site + cancer separated in the abstract) and yields
less than half of A. A applies the identical C8 principle as nasopharynx.

### Other pharynx yearly counts, original vs precise (A)

| Year | Original | Precise A |
|---|---|---|
| 1995 | 254 | 176 |
| 1996 | 314 | 189 |
| 1997 | 293 | 192 |
| 1998 | 361 | 208 |
| 1999 | 367 | 223 |
| 2000 | 378 | 246 |
| 2001 | 369 | 216 |
| 2002 | 454 | 285 |
| 2003 | 406 | 269 |
| 2004 | 448 | 300 |
| 2005 | 463 | 308 |
| 2006 | 537 | 357 |
| 2007 | 516 | 314 |
| 2008 | 526 | 342 |
| 2009 | 675 | 410 |
| 2010 | 691 | 437 |
| 2011 | 727 | 465 |
| 2012 | 901 | 619 |
| 2013 | 989 | 657 |
| 2014 | 1,105 | 745 |
| 2015 | 1,150 | 768 |
| 2016 | 1,247 | 875 |
| 2017 | 1,289 | 910 |
| 2018 | 1,383 | 929 |
| 2019 | 1,447 | 1,017 |
| 2020 | 2,070 | 1,204 |
| 2021 | 2,418 | 1,392 |
| 2022 | 2,110 | 1,184 |
| 2023 | 1,932 | 1,193 |
| 2024 | 1,943 | 1,162 |
| **Total** | **27,763** | **17,592** |

## 3. oral_cancer — FREEZE: original + lip expressions (GBD 444 is LIP and oral cavity)

- **Precise (frozen):** `TITLE_ABS:("oral cancer" OR "oral cavity cancer" OR "mouth cancer" OR "oral squamous" OR "lip cancer" OR "lip carcinoma" OR "lip squamous" OR "lip neoplasm" OR "lip neoplasms")`
- Lip terms alone total 573; union total 29,957 vs original
  29,470 → **net lip increment +487 records
  (+98 in 2020–2024)**. Small but systematic: the GBD cause's lip
  component was previously counted nowhere.

### Oral yearly counts, original vs precise (+lip)

| Year | Original | Precise +lip |
|---|---|---|
| 1995 | 186 | 196 |
| 1996 | 211 | 221 |
| 1997 | 245 | 252 |
| 1998 | 245 | 253 |
| 1999 | 309 | 319 |
| 2000 | 317 | 325 |
| 2001 | 360 | 373 |
| 2002 | 383 | 386 |
| 2003 | 416 | 430 |
| 2004 | 431 | 442 |
| 2005 | 517 | 530 |
| 2006 | 524 | 537 |
| 2007 | 585 | 596 |
| 2008 | 638 | 652 |
| 2009 | 682 | 702 |
| 2010 | 789 | 808 |
| 2011 | 869 | 883 |
| 2012 | 994 | 1,013 |
| 2013 | 1,012 | 1,028 |
| 2014 | 1,141 | 1,165 |
| 2015 | 1,328 | 1,346 |
| 2016 | 1,346 | 1,373 |
| 2017 | 1,438 | 1,467 |
| 2018 | 1,480 | 1,511 |
| 2019 | 1,611 | 1,638 |
| 2020 | 1,953 | 1,980 |
| 2021 | 2,255 | 2,266 |
| 2022 | 2,364 | 2,380 |
| 2023 | 2,306 | 2,332 |
| 2024 | 2,535 | 2,553 |
| **Total** | **29,470** | **29,957** |

## 4. larynx_cancer — FREEZE: original + three measured expression groups

- **Precise (frozen):** `TITLE_ABS:("laryngeal cancer" OR "larynx cancer" OR "laryngeal carcinoma" OR "cancer of the larynx" OR "cancer of larynx" OR "glottic cancer" OR "glottic carcinoma" OR "supraglottic cancer" OR "supraglottic carcinoma" OR "subglottic cancer" OR "subglottic carcinoma" OR "laryngeal neoplasm" OR "laryngeal neoplasms" OR "laryngeal malignancy" OR "larynx carcinoma")`
- Every added expression carries a cancer limiter or is a cancer-specific phrase.
  Group totals alone (1995–2024): "cancer of the larynx/larynx" 523;
  subsite (glottic/supraglottic/subglottic cancer & carcinoma) 1,657;
  neoplasm/malignancy/"larynx carcinoma" 523.
  Union total 9,767 vs original 7,821 → **net increment
  +1,946 (+24.9%)** — the original query materially
  undercounted larynx cancer, the mirror image of the nasopharynx problem.

### Larynx yearly counts, original vs precise (union)

| Year | Original | Precise union |
|---|---|---|
| 1995 | 170 | 233 |
| 1996 | 154 | 200 |
| 1997 | 169 | 229 |
| 1998 | 178 | 239 |
| 1999 | 177 | 236 |
| 2000 | 205 | 271 |
| 2001 | 176 | 251 |
| 2002 | 195 | 245 |
| 2003 | 207 | 273 |
| 2004 | 241 | 292 |
| 2005 | 228 | 291 |
| 2006 | 228 | 293 |
| 2007 | 234 | 302 |
| 2008 | 245 | 315 |
| 2009 | 248 | 312 |
| 2010 | 247 | 305 |
| 2011 | 254 | 308 |
| 2012 | 260 | 327 |
| 2013 | 282 | 350 |
| 2014 | 332 | 404 |
| 2015 | 324 | 392 |
| 2016 | 351 | 431 |
| 2017 | 336 | 403 |
| 2018 | 294 | 369 |
| 2019 | 323 | 402 |
| 2020 | 368 | 432 |
| 2021 | 375 | 441 |
| 2022 | 359 | 425 |
| 2023 | 329 | 405 |
| 2024 | 332 | 391 |
| **Total** | **7,821** | **9,767** |

## 5. crs_polyps — handling proposal (FROZEN as: precise main + dual sensitivity reporting)

Counts (1995–2024 totals): original (with standalone "sinusitis")
28,045; without standalone sinusitis (keeps rhinosinusitis,
"chronic sinusitis", nasal polyp(s), + CRSwNP/CRSsNP/"nasal polyposis")
19,111; standalone "sinusitis" alone 14,270.
8,934 records enter the original area **only** through the
standalone word "sinusitis" — predominantly acute/general sinusitis, off-entity
for a chronic-disease area.

**Decision:** the precise main query drops standalone "sinusitis":
`TITLE_ABS:(rhinosinusitis OR "chronic sinusitis" OR "nasal polyp" OR "nasal polyps" OR CRSwNP OR CRSsNP OR "nasal polyposis")`.
Because the frozen backup query (modern terminology only) previously reversed
this area's trend, CRS/polyps must be **triple-reported** in the revised
manuscript: precise main, original, and frozen backup
(1995–2024 backup total 11,769) — and its share trend is not a headline
in any formulation. Rationale: removing a known off-entity term is the same
correction principle as the cancer areas; keeping the original as a reported
sensitivity preserves comparability with the frozen round.

### CRS/polyps yearly counts, original vs precise (minus standalone sinusitis)

| Year | Original | Precise |
|---|---|---|
| 1995 | 363 | 168 |
| 1996 | 401 | 174 |
| 1997 | 480 | 235 |
| 1998 | 511 | 214 |
| 1999 | 511 | 252 |
| 2000 | 572 | 290 |
| 2001 | 586 | 285 |
| 2002 | 540 | 293 |
| 2003 | 634 | 357 |
| 2004 | 714 | 391 |
| 2005 | 766 | 483 |
| 2006 | 822 | 508 |
| 2007 | 840 | 565 |
| 2008 | 884 | 549 |
| 2009 | 886 | 577 |
| 2010 | 857 | 575 |
| 2011 | 913 | 633 |
| 2012 | 984 | 690 |
| 2013 | 1,068 | 803 |
| 2014 | 1,048 | 756 |
| 2015 | 1,058 | 779 |
| 2016 | 1,119 | 853 |
| 2017 | 1,068 | 815 |
| 2018 | 1,136 | 842 |
| 2019 | 1,258 | 925 |
| 2020 | 1,334 | 1,037 |
| 2021 | 1,523 | 1,154 |
| 2022 | 1,653 | 1,232 |
| 2023 | 1,660 | 1,262 |
| 2024 | 1,856 | 1,414 |
| **Total** | **28,045** | **19,111** |

## 6. hearing_loss — checked, NOT changed (explicit justification)

The query stays `TITLE_ABS:("hearing loss" OR "hearing impairment" OR deafness OR presbycusis)`.
Justification: (i) the audit found no false-positive mechanism for this area —
its terms are disease terms, not anatomy/sampling words; (ii) GBD cause 674 is
itself "age-related **and other** hearing loss", i.e. the burden cause is also
broad by construction, so a broad literature set is calibre-aligned in kind;
(iii) narrowing to age-related wording (e.g. requiring presbycusis) would
redefine the area mid-project and destroy comparability with the frozen
attention-tier design. The residual calibre difference (literature wording
cannot mirror GBD's severity/aetiology modelling) is qualitative and is
recorded in mapping_table.csv/md.

## 7. All other areas — checked and unchanged

otitis_media, thyroid_cancer, allergic_rhinitis, osa, tinnitus, vertigo,
cholesteatoma, cochlear_implant: each formulation is built from
disease/entity-specific phrases with no anatomy-only or sampling-word term;
the audit's false-positive mechanism does not apply. Thyroid (burden tier) is
fully cancer-limited in every term group. Vertigo's text-vs-query scope
mismatch (text: Ménière/BPPV; query: all vertigo) is recorded in the mapping
table and left for the manuscript stage, not silently fixed here. Their L1
recount values are asserted equal to the frozen table in the recount script
(any API-drift cell is logged, frozen value kept).

## 8. Frozen precise set (for L1 recount and Stage 2)

| Area | Status | Precise query |
|---|---|---|
| nasopharynx_cancer | CHANGED | `TITLE_ABS:((nasopharyngeal OR nasopharynx) AND (cancer OR carcinoma OR malignancy OR malignant OR neoplasm OR tumour OR tumor OR oncology))` |
| other_pharynx_cancer | CHANGED | `TITLE_ABS:((oropharyngeal OR hypopharyngeal OR oropharynx OR hypopharynx) AND (cancer OR carcinoma OR malignancy OR malignant OR neoplasm OR tumour OR tumor OR oncology))` |
| oral_cancer | CHANGED | original phrases + lip phrases (§3) |
| larynx_cancer | CHANGED | original phrases + 12 added cancer-limited phrases (§4) |
| crs_polyps | CHANGED | minus standalone "sinusitis", + CRSwNP/CRSsNP/"nasal polyposis" (§5) |
| hearing_loss + 8 others | UNCHANGED | original queries verbatim |

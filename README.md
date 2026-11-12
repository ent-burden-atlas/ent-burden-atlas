# ENT Burden Atlas

**Research attention vs disease burden in otolaryngology, 1995–2024 — a preregistered dynamic census.**

This repository holds the static atlas website, the full production code and the
frozen result tables of the census. Publications were counted in Europe PMC for
14 disease areas (392,456 retrievable records, 1995–2024); for the seven areas
with a matched Global Burden of Disease (GBD) 2023 cause, output is set against
DALY burden (1995–2023) through four layers: publication-share dynamics, the
attention–burden ratio (ABR), geographic double-centroid distances and
first-author shares, and a rule-based decoupling typology.

- **Canonical site:** https://burden.erbihou.org/ (GitHub Pages mirror:
  https://yuye8848.github.io/ent-burden-atlas/)
- **Preregistration:** OSF, DOI [10.17605/OSF.IO/NUC4B](https://doi.org/10.17605/OSF.IO/NUC4B)
- **Frozen data & code archive:** Zenodo, DOI
  [10.5281/zenodo.24157110](https://doi.org/10.5281/zenodo.24157110)
  (includes the record-level country-parse table for all 392,456 records, the
  GBD input extracts, reference tables and the protocol documents)
- **Manuscript:** in preparation for *Scientometrics* (not yet published).

## Repository layout

- `/` — the static website (pure HTML/CSS with build-time inline SVG charts;
  no JavaScript framework, no tracking). `index.html`, `areas.html`,
  `areas/*.html` (14 area pages), `findings.html`, `geography.html`,
  `typology.html`, `methods.html`, `downloads.html`, `about.html`.
- `/zh/` — the full Chinese mirror of every page above (English is the
  default at the root URLs; each page carries a 中文 / EN toggle).
- `/downloads/` — the frozen result tables (CSV) behind every number on the
  site, plus `frozen_tables.zip`.
- `/code/scripts/` — production pipeline (publication census, GBD mapping,
  ABR, country parsing, centroids, typology, sensitivity analyses).
- `/code/figures_scripts/` — R scripts that render the manuscript figures
  directly from the frozen tables.
- `/code/build_site.py` — the generator that rebuilds the website from the
  frozen tables (it asserts every headline number before writing a page).
- `/code/prep_zenodo.py` — the script that staged the Zenodo archive.

## Reading rules

"Resolution" and burden decline always denote *relative share dilution* inside
the defined pools — annualised absolute DALYs rose for all seven burden-tier
causes. The chronic rhinosinusitis / nasal polyps share decline carries a
terminology-migration caveat and is not a headline conclusion. Hearing loss's
"constant" typology label describes dynamics only; its level is ABR 0.36 in
2020–24, the deepest deficit in the census. Laryngeal, other pharyngeal and
thyroid cancer are reported as *unclassified* under the main typology
thresholds, not forced into a type. The census measures the configuration of
research allocation only; it makes no judgement about the clinical value of
research on any disease.

## Citation and reuse

Frozen data tables: CC-BY 4.0, as in the Zenodo record. If you reuse the
pipeline for another specialty, please cite the Zenodo archive and the OSF
registration above.

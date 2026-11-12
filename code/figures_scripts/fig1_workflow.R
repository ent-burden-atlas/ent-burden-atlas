#!/usr/bin/env Rscript
# Fig 1 — Study workflow (PRISMA-2020 flow grammar).
# Skeleton: text node spec approved by the user 2026-11-12 (this script renders
#   exactly that structure; wording tightened only to fit boxes, no number changed).
# Governing protocol: user ruling 2026-11-09 — workflow figures use PRISMA-2020
#   flow grammar, vertical main stream, every box carries its n, exclusions and
#   notes branch off the side, boxes contain TEXT ONLY (no icons/glyphs). This
#   protocol OVERRIDES figure_style_v3 V5 (schematic icon rule) for this figure,
#   and adapts V1 (box text is mandated by the approved spec). See fig1_v3check.md.
# Chart-selection table (SKILL §二) has no flow-diagram type; per §一.2 the reason
#   is recorded here: a study-flow diagram's "data structure" is the pipeline
#   itself, and the 2026-11-09 ruling fixes its grammar.
# IRON RULE: every printed count is computed from the frozen files below and
#   hard-asserted with stopifnot BEFORE anything is drawn; the strings rendered
#   on the figure are built from those asserted values, never typed from memory.
# RUN NOTE: execute with LC_ALL=C.utf8 — under this machine's default ASCII
#   locale the ·, ×, − and – glyphs in box text render as dots in the PNG.
source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages(library(jsonlite))

ROOT <- "~/workspace/ent-attention-burden"
fmt <- function(x) formatC(x, format = "d", big.mark = ",")

## ---- Assertions against frozen records (all must pass before drawing) -------
# L1 yearly counts: 420 cells, pool window totals (spec-mandated assertions).
l1 <- read.csv(file.path(ROOT, "data_l1/l1_counts_by_year.csv"))
stopifnot(nrow(l1) == 420L, length(unique(l1$area)) == 14L)
stopifnot(sum(l1$count[l1$year >= 1995 & l1$year <= 1999]) == 26544,
          sum(l1$count[l1$year >= 2020 & l1$year <= 2024]) == 128117)

# L3 pull: 84 parts; .done metadata sums (hitCount total, affiliation availability).
done_files <- list.files(file.path(ROOT, "data_l3/parts"),
                         pattern = "\\.jsonl\\.done$", full.names = TRUE)
stopifnot(length(done_files) == 84L)
.done <- lapply(done_files, jsonlite::fromJSON)
n_hit  <- sum(vapply(.done, function(m) as.numeric(m$hit_count), numeric(1)))
n_aff  <- sum(vapply(.done, function(m) as.numeric(m$with_first_affiliation),
                     numeric(1)))
stopifnot(n_hit == 392458, n_aff == 356332)

# L3 parsing coverage (frozen table): retrieved / parsed / unparsed / missing.
pc <- read.csv(file.path(ROOT, "data_l3/geo/parse_coverage.csv"))
stopifnot(nrow(pc) == 84L,
          sum(pc$records)  == 392456,
          sum(pc$with_aff) == 356332,
          sum(pc$parsed)   == 340582,
          sum(pc$unparsed) == 15750,
          sum(pc$missing)  == 36124)
n_ret   <- sum(pc$records); n_parsed <- sum(pc$parsed)
n_unpar <- sum(pc$unparsed); n_miss  <- sum(pc$missing)
stopifnot(n_hit - n_ret == 2)                       # the two phantom records
pct_aff    <- round(100 * n_aff / n_ret, 2)
pct_parsed <- round(100 * n_parsed / n_aff, 2)
stopifnot(pct_aff == 90.80, pct_parsed == 95.58)

# Country units from the frozen country-count table.
cc <- read.csv(file.path(ROOT, "data_l3/geo/country_counts.csv"))
n_units <- length(unique(cc$iso3)); stopifnot(n_units == 159L)

# L2 burden files: 14 raw GBD 2023 CSVs (7 causes x DALYs/prevalence).
stopifnot(length(list.files(file.path(ROOT, "data_l2/raw"),
                            pattern = "\\.csv$")) == 14L)
# L2/L3 analysis cells: ABR grid and double-centroid grid, 42 cells each.
n_abr <- nrow(read.csv(file.path(ROOT, "data_l2/abr/abr_primary.csv")))
n_cen <- nrow(read.csv(file.path(ROOT, "data_l3/geo/centroid/double_centroid.csv")))
stopifnot(n_abr == 42L, n_cen == 42L)
# L4 typology: 7 burden causes, exactly 3 unclassified at main thresholds.
ty <- read.csv(file.path(ROOT, "data_l4/typology.csv"))
ty_b <- ty[ty$tier == "burden", ]
stopifnot(nrow(ty) == 14L, nrow(ty_b) == 7L,
          sum(ty_b$type_main == "unclassified") == 3L)
message("Fig 1: all stopifnot assertions passed ",
        "(392,458 / 392,456 / 356,332 / 340,582 / 420 / 42 / 159 / windows).")

## ---- Layout ------------------------------------------------------------------
# Canvas 180 x 226 mm. Plot coords = mm; helper T() converts "mm from top".
W <- 180; H <- 226
T <- function(top) H - top
NAVY <- COL$disease2; RED <- COL$disease1; TXT <- COL$grey_txt
NEUT <- COL$neutral;  BROWN <- COL$accent
FILL_MAIN <- "white"; FILL_GBD <- "#EDF1F6"; FILL_CONT <- "#F4F6F9"

# columns: left exclusion x 3-41 | main stream x 47-121 (centre 84) | right x 127-177
MX <- 84   # main-stream centre
RX <- 152  # right-column centre

p <- ggplot() +
  scale_x_continuous(limits = c(0, W), expand = c(0, 0)) +
  scale_y_continuous(limits = c(0, H), expand = c(0, 0)) +
  coord_fixed(ratio = 1) +
  theme_void() +
  theme(plot.margin = margin(0, 0, 0, 0),
        text = element_text(family = "Arial"))

# primitives ---------------------------------------------------------------------
rect <- function(x0, x1, top, bot, fill, border, lty = "solid", lwd = 0.6)
  p <<- p + annotate("rect", xmin = x0, xmax = x1, ymin = T(bot), ymax = T(top),
                     fill = fill, colour = border, linetype = lty,
                     linewidth = lwd)
hdr <- function(x0, x1, top, label, fill = NAVY) {
  p <<- p + annotate("rect", xmin = x0, xmax = x1, ymin = T(top + 6.4),
                     ymax = T(top), fill = fill, colour = fill) +
    annotate("text", x = (x0 + x1) / 2, y = T(top + 3.35), label = label,
             size = 2.95, fontface = "bold", colour = "white",
             family = "Arial")
}
# stacked text lines, top-down; each entry: c(text, size, bold, colour, extra_gap)
lines_at <- function(x, top_start, entries, align = "centre") {
  y <- top_start
  for (e in entries) {
    sz <- as.numeric(e[2]); gap <- if (length(e) >= 5) as.numeric(e[5]) else 0
    y <- y + gap
    p <<- p + annotate("text", x = x, y = T(y + sz * 0.5), label = e[1],
                       size = sz, fontface = if (e[3] == "1") "bold" else "plain",
                       colour = e[4], family = "Arial",
                       hjust = if (align == "centre") 0.5 else 0)
    y <- y + sz * 1.38
  }
  invisible(y)
}
arrow_v <- function(x, top_from, top_to)
  p <<- p + annotate("segment", x = x, xend = x, y = T(top_from), yend = T(top_to),
                     colour = NAVY, linewidth = 0.55,
                     arrow = arrow(length = unit(2.3, "mm"), type = "closed"))
seg <- function(x0, x1, y0, y1, col = NAVY, lty = "solid", lwd = 0.55)
  p <<- p + annotate("segment", x = x0, xend = x1, y = T(y0), yend = T(y1),
                     colour = col, linetype = lty, linewidth = lwd)
note_conn <- function(top_y)  # dashed connector, container right edge -> note
  seg(121, 127, top_y, top_y, col = NEUT, lty = "dashed", lwd = 0.45)

## ---- Right column, top: URI side note (disease-pool level, dashed) ----------
rect(127, 177, 2, 21, "white", NEUT, "dashed", 0.5)
lines_at(RX, 4.6, list(
  c("Upper respiratory infections", "2.47", "0", TXT),
  c("excluded a priori (not an ENT", "2.47", "0", TXT),
  c("research corpus)",             "2.47", "0", TXT)))
seg(121, 127, 11.5, 11.5, col = NEUT, lty = "dashed", lwd = 0.45)

## ---- Main box 1: identification ----------------------------------------------
rect(47, 121, 2, 29, FILL_MAIN, NAVY, lwd = 0.65)
hdr(47, 121, 2, "Identification · Europe PMC")
lines_at(MX, 10.6, list(
  c("Record-level retrieval",                 "2.65", "0", TXT),
  c("84 parts (14 areas × 6 periods)",        "2.65", "0", TXT),
  c(paste0("n = ", fmt(n_hit), " records identified"), "2.7", "1", TXT, 1.6),
  c("(hitCount total)",                       "2.47", "0", TXT)))

## ---- Phantom exclusion branch (exits left, red accent) -----------------------
p <- p + annotate("segment", x = MX, xend = 41.6, y = T(36), yend = T(36),
                  colour = RED, linewidth = 0.55,
                  arrow = arrow(length = unit(2.3, "mm"), type = "closed"))
rect(3, 41, 25, 47, "white", RED, lwd = 0.7)
p <- p + annotate("rect", xmin = 3, xmax = 41, ymin = T(31.4), ymax = T(25),
                  fill = RED, colour = RED) +
  annotate("text", x = 22, y = T(28.35), label = "Excluded", size = 2.8,
           fontface = "bold", colour = "white", family = "Arial")
lines_at(22, 33.2, list(
  c("2 phantom records (D-1, D-2):",  "2.4", "0", TXT),
  c("hitCount − retrievable = 1 each,", "2.4", "0", TXT),
  c("auto-filed",                     "2.4", "0", TXT)))

## ---- Main box 1b: retrieved ----------------------------------------------------
arrow_v(MX, 29, 40)
rect(47, 121, 40, 55, FILL_MAIN, NAVY, lwd = 0.65)
lines_at(MX, 42.2, list(
  c("Records retrieved", "2.8", "1", NAVY),
  c(paste0("n = ", fmt(n_ret)), "2.8", "1", TXT, 0.8)))

## ---- Main box 2: affiliation ---------------------------------------------------
arrow_v(MX, 55, 61)
rect(47, 121, 61, 82, FILL_MAIN, NAVY, lwd = 0.65)
hdr(47, 121, 61, "Affiliation availability")
lines_at(MX, 69.6, list(
  c("First-author affiliation available", "2.65", "0", TXT),
  c(paste0("n = ", fmt(n_aff), " (", sprintf("%.2f", pct_aff), "%)"),
    "2.7", "1", TXT, 1.6)))

## ---- Main box 3: geographic parsing --------------------------------------------
arrow_v(MX, 82, 88)
rect(47, 121, 88, 117, FILL_MAIN, NAVY, lwd = 0.65)
hdr(47, 121, 88, "Geographic parsing")
lines_at(MX, 95.8, list(
  c("Country parsed from affiliation",       "2.65", "0", TXT),
  c("(dictionary matching, no imputation)",  "2.65", "0", TXT),
  c(paste0("n = ", fmt(n_parsed), " (", sprintf("%.2f", pct_parsed),
           "% of available)"),               "2.7", "1", TXT, 1.4),
  c(paste0(fmt(n_units), " country/region units"), "2.65", "0", TXT),
  c(paste0("Not parsed ", fmt(n_unpar), " · affiliation missing ",
           fmt(n_miss)),                     "2.3", "0", COL$grey_ax, 0.6)))

## ---- Right stream: GBD burden data ----------------------------------------------
rect(127, 177, 27, 58, FILL_GBD, NAVY, lwd = 0.65)
hdr(127, 177, 27, "Burden data · GBD 2023")
lines_at(RX, 35.6, list(
  c("14 files (7 causes ×",      "2.65", "0", TXT),
  c("DALYs / prevalence)",       "2.65", "0", TXT),
  c("205 locations · 1995–2023", "2.65", "0", TXT, 1.2)))
# amendment note, dashed, attached under the GBD box
seg(152, 152, 58, 62, col = NEUT, lty = "dashed", lwd = 0.45)
rect(127, 177, 62, 81, "white", NEUT, "dashed", 0.5)
lines_at(RX, 64.4, list(
  c("Source amended from GBD 2021", "2.47", "0", TXT),
  c("(retired) — Amendment v1.1,",  "2.47", "0", TXT),
  c("OSF-registered",               "2.47", "0", TXT)))
# join path: GBD left edge -> down the x=124 channel -> into container top
seg(127, 124, 42, 42); seg(124, 124, 42, 119); seg(124, 104, 119, 119)
p <- p + annotate("segment", x = 104, xend = 104, y = T(119), yend = T(122.4),
                  colour = NAVY, linewidth = 0.55,
                  arrow = arrow(length = unit(2.3, "mm"), type = "closed"))

## ---- Step 4: analysis layers (container with four sub-boxes) -------------------
arrow_v(MX, 117, 123)
rect(47, 121, 123, 199, FILL_CONT, NAVY, lwd = 0.65)
hdr(47, 121, 123, "Analysis layers")
sub <- function(top, bot, title, body) {
  rect(51, 117, top, bot, "white", NEUT, lwd = 0.55)
  lines_at(MX, top + 2.0, c(list(c(title, "2.7", "1", NAVY)), body))
}
sub(135, 149, "L1 · Share dynamics", list(
  c("14 areas × 6 periods — yearly counts,", "2.6", "0", TXT),
  c(paste0("n = ", nrow(l1), " cells"),      "2.6", "0", TXT)))
sub(151, 162, "L2 · Attention–burden ratio (ABR)", list(
  c(paste0("7 burden causes × 6 periods = ", n_abr, " cells"), "2.6", "0", TXT)))
sub(164, 178, "L3 · Geographic alignment", list(
  c(paste0("Double-centroid distance: ", n_cen, " cells"), "2.6", "0", TXT),
  c("LMIC + top-10-burden-country author shares",          "2.6", "0", TXT)))
sub(180, 197.5, "L4 · Decoupling typology", list(
  c("7 burden causes typed (3 unclassified,",  "2.6", "0", TXT),
  c("reported as such) · 7 attention areas:", "2.6", "0", TXT),
  c("share-dynamics labels only",             "2.6", "0", TXT)))

## ---- Side notes for L1 and L2 (dashed, right of the container) ------------------
note_conn(143)
rect(127, 177, 133, 152, "white", NEUT, "dashed", 0.5)
lines_at(RX, 135.4, list(
  c("Otitis media includes chronic", "2.47", "0", TXT),
  c("suppurative otitis media —",    "2.47", "0", TXT),
  c("not separable",                 "2.47", "0", TXT)))
note_conn(162.5)
rect(127, 177, 157, 183, "white", NEUT, "dashed", 0.5)
lines_at(RX, 159.4, list(
  c("Attention tier (7 areas): no GBD", "2.47", "0", TXT),
  c("cause — no burden numbers",        "2.47", "0", TXT),
  c("Last period: burden 2020–23 vs",   "2.47", "0", TXT, 1.8),
  c("publications 2020–24",             "2.47", "0", TXT)))

## ---- Step 5: outputs --------------------------------------------------------------
arrow_v(MX, 199, 203)
rect(47, 121, 203, 222, FILL_MAIN, NAVY, lwd = 0.65)
hdr(47, 121, 203, "Outputs")
lines_at(MX, 211.2, list(
  c("Misalignment atlas website · open pipeline", "2.6", "0", TXT),
  c("repository · Zenodo frozen archive · OSF",   "2.6", "0", TXT),
  c("preregistration (DOI 10.17605/OSF.IO/NUC4B)", "2.6", "0", TXT)))

save_fig(p, file.path(ROOT, "figures/fig1"), width_mm = 180, height_mm = 226)
message("Fig 1 rendered: figures/fig1.pdf + figures/fig1.png")

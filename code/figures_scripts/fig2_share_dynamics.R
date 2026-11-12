#!/usr/bin/env Rscript
# Fig 2 — Share dynamics of the 14-area publication pool, 1995-2024.
# Run from the project root:  Rscript figures/scripts/fig2_share_dynamics.R
#
# Conclusions carried (figure_style_v3 section 1.1, conclusion-first):
#   C1 (panel a, anchor): the pool's composition was re-ordered over 30 years -
#      hearing loss stays the largest band but shrinks, while the cancer bands
#      (nasopharynx, thyroid, oral) expand to near half the pool.
#   C2 (panel b): within the burden tier, otitis media's share collapsed
#      (8.4% -> 2.9%) even as its absolute output rose (2,229 -> 3,706 per
#      5-year window); laryngeal cancer's share more than halved.
#   C3 (panel c): within the attention tier, OSA stepped up before 2005-09 and
#      then plateaued at ~13%; CRS/polyps declined on the primary-query basis
#      (terminology caveat, asterisk; see caption).
# Teardown rules applied (figures/teardown_notes.md): R1 anchor panel carries
#   the composition stream, other panels carry the accounting (endpoint
#   dumbbell labels, aligned numbers); R3 direct labels instead of legends.
# Source (frozen, read-only): data_l1/l1_counts_by_year.csv (all panels).
# IRON RULE: every printed number is computed from that file and asserted
#   below; assertions failing stops the build.

source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages({
  library(patchwork)
  library(colorspace)
})

## ---- data -------------------------------------------------------------------
d <- read.csv("data_l1/l1_counts_by_year.csv", stringsAsFactors = FALSE)
BURDEN   <- c("otitis_media", "hearing_loss", "larynx_cancer", "oral_cancer",
              "nasopharynx_cancer", "other_pharynx_cancer", "thyroid_cancer")
ATTENTION <- c("crs_polyps", "allergic_rhinitis", "osa", "tinnitus", "vertigo",
               "cholesteatoma", "cochlear_implant")
CANCERS  <- c("larynx_cancer", "oral_cancer", "nasopharynx_cancer",
              "other_pharynx_cancer", "thyroid_cancer")
stopifnot(nrow(d) == 420L, length(unique(d$area)) == 14L,
          setequal(unique(d$area), c(BURDEN, ATTENTION)),
          all(tapply(d$year, d$area, function(x) setequal(x, 1995:2024))))

# yearly shares within the 14-area pool
d <- d %>% group_by(year) %>% mutate(share = count / sum(count) * 100) %>%
  ungroup()

# 5-year window shares and counts
WIN_LAB <- c("1995-99", "2000-04", "2005-09", "2010-14", "2015-19", "2020-24")
WIN_X   <- c(1995, 2000, 2005, 2010, 2015, 2020)  # window start years
w <- d %>%
  mutate(win = cut(year, breaks = c(1994, 1999, 2004, 2009, 2014, 2019, 2024),
                   labels = WIN_LAB)) %>%
  group_by(area, win) %>% summarise(n = sum(count), .groups = "drop") %>%
  group_by(win) %>% mutate(share = n / sum(n) * 100) %>% ungroup() %>%
  mutate(x = WIN_X[match(win, WIN_LAB)])

## ---- assertions (tolerance 0.6 pp on shares) --------------------------------
tol <- 0.6
pool_win <- w %>% group_by(win) %>% summarise(tot = sum(n), .groups = "drop")
stopifnot(pool_win$tot[pool_win$win == "1995-99"] == 26544,
          pool_win$tot[pool_win$win == "2020-24"] == 128117)
fc <- w %>% filter(area %in% CANCERS) %>% group_by(win) %>%
  summarise(s = sum(share), .groups = "drop")
stopifnot(abs(fc$s[fc$win == "1995-99"] - 32.1) < tol,
          abs(fc$s[fc$win == "2020-24"] - 44.6) < tol)
wsh <- function(a, wn) w$share[w$area == a & w$win == wn]
wn_ <- function(a, wn) w$n[w$area == a & w$win == wn]
stopifnot(abs(wsh("otitis_media", "1995-99") - 8.4) < tol,
          abs(wsh("otitis_media", "2020-24") - 2.9) < tol,
          wn_("otitis_media", "1995-99") == 2229,
          wn_("otitis_media", "2020-24") == 3706,
          abs(wsh("hearing_loss", "1995-99") - 20.4) < tol,
          abs(wsh("hearing_loss", "2020-24") - 16.9) < tol)
# OSA plateau phrase in panel c: all windows from 2005-09 on lie within 12-14%
osa_win <- w$share[w$area == "osa"][3:6]
stopifnot(all(osa_win >= 12 & osa_win <= 14))
cat("assertions passed: pool 26,544 -> 128,117; five-cancer 32.1% -> 44.6%;",
    "otitis 8.4% -> 2.9% (2,229 -> 3,706); hearing 20.4% -> 16.9%",
    "OSA plateau 12-14% since 2005-09\n")

## ---- display layer: labels and colours (V8 mapping, display only) -----------
LAB <- c(hearing_loss = "Hearing loss", otitis_media = "Otitis media",
         nasopharynx_cancer = "Nasopharyngeal cancer",
         thyroid_cancer = "Thyroid cancer", oral_cancer = "Oral cancer",
         other_pharynx_cancer = "Other pharyngeal cancer",
         larynx_cancer = "Laryngeal cancer",
         osa = "Obstructive sleep apnoea", crs_polyps = "CRS / polyps *",
         allergic_rhinitis = "Allergic rhinitis",
         cochlear_implant = "Cochlear implant", tinnitus = "Tinnitus",
         vertigo = "Vertigo", cholesteatoma = "Cholesteatoma")
# Colour harmonisation 2026-11-12: the 7 burden-tier causes use exactly the
# shared CCOL hex values of Fig 3 / Fig 4 (one colour per cause, paper-wide).
# Attention-tier areas keep desaturated hues, except allergic_rhinitis
# (lightened: its old #8491B4 is now larynx_cancer's CCOL) and vertigo
# (greyed further: its base hue #3C5488 is now oral_cancer's CCOL) - hue
# family kept in both cases.
base <- pal_cat(12)  # E64B35 3C5488 4DBBD5 7E6148 8491B4 00A087 F39B7F
                     # 91D1C2 DC0000 7E7E7E B09C00 5B4E77
CCOL <- c(otitis_media = "#4DBBD5", hearing_loss = "#E64B35",
          larynx_cancer = "#8491B4", oral_cancer = "#3C5488",
          nasopharynx_cancer = "#DC0000", other_pharynx_cancer = "#7E6148",
          thyroid_cancer = "#8FAE94")   # identical to fig4_abr.R / fig5_geography.R
AREA_COL <- c(
  hearing_loss         = CCOL[["hearing_loss"]],         # #E64B35 red
  otitis_media         = CCOL[["otitis_media"]],         # #4DBBD5 blue
  nasopharynx_cancer   = CCOL[["nasopharynx_cancer"]],   # #DC0000 deep red
  oral_cancer          = CCOL[["oral_cancer"]],          # #3C5488 navy
  thyroid_cancer       = CCOL[["thyroid_cancer"]],       # #8FAE94 sage
  other_pharynx_cancer = CCOL[["other_pharynx_cancer"]], # #7E6148 brown
  larynx_cancer        = CCOL[["larynx_cancer"]],        # #8491B4 grey-blue
  osa                  = desaturate(base[6], 0.25),  # teal, muted
  crs_polyps           = base[8],                    # #91D1C2 pale teal
  cochlear_implant     = desaturate(base[6], 0.55),  # teal, greyed
  allergic_rhinitis    = lighten(base[5], 0.3),      # grey-blue, lightened (was #8491B4 = CCOL larynx)
  tinnitus             = base[12],                   # #5B4E77 muted purple
  vertigo              = desaturate(base[2], 0.55),  # navy, greyed further (base hue = CCOL oral)
  cholesteatoma        = base[10]                    # #7E7E7E grey
)
STACK <- c("hearing_loss", "otitis_media", "nasopharynx_cancer", "oral_cancer",
           "thyroid_cancer", "other_pharynx_cancer", "larynx_cancer", "osa",
           "crs_polyps", "cochlear_implant", "allergic_rhinitis", "tinnitus",
           "vertigo", "cholesteatoma")
d$area <- factor(d$area, levels = STACK)

## ---- panel a: 100% stacked area (anchor) ------------------------------------
# geom_area stacks the last factor level at the bottom, so the panel-a copy
# uses reversed levels: bottom-to-top order then equals STACK, which is also
# the order used for the label midpoints below.
pa_dat <- d %>% mutate(area = factor(area, levels = rev(STACK)))
lab_a <- d %>% filter(year >= 2022) %>% group_by(area) %>%
  summarise(m = mean(share), .groups = "drop") %>%
  arrange(match(area, STACK)) %>%
  mutate(ymid = cumsum(m) - m / 2)
LAB_A <- c(hearing_loss = "Hearing loss", nasopharynx_cancer = "Nasopharynx",
           thyroid_cancer = "Thyroid", osa = "OSA", oral_cancer = "Oral",
           crs_polyps = "CRS / polyps")
# Direct labels sit inside the bands at the right edge (no legend); white on
# the dark bands, dark grey on the two light bands (sage, pale teal).
# Harmonisation 2026-11-12: oral_cancer band is now navy (#3C5488) so its
# label flips to white; thyroid_cancer band is now sage (#8FAE94) so its
# label flips to dark grey.
TCOL_A <- c(hearing_loss = "white", nasopharynx_cancer = "white",
            thyroid_cancer = "#333333", osa = "white",
            oral_cancer = "white", crs_polyps = "#333333")
lab_a <- lab_a %>% filter(area %in% names(LAB_A)) %>%
  mutate(txt = LAB_A[as.character(area)],
         tcol = TCOL_A[as.character(area)])

pa <- ggplot(pa_dat, aes(year, share, fill = area)) +
  geom_area(position = "stack", colour = "white", linewidth = 0.15) +
  geom_text(data = lab_a, aes(x = 2023.7, y = ymid, label = txt,
                              colour = area),
            hjust = 1, size = 2.6, fontface = "bold", inherit.aes = FALSE) +
  scale_fill_manual(values = AREA_COL, guide = "none") +
  scale_colour_manual(values = lab_a$tcol, guide = "none") +
  scale_x_continuous(breaks = c(1995, 2005, 2015, 2024),
                     expand = expansion(mult = c(0, 0.005))) +
  scale_y_continuous(breaks = c(0, 25, 50, 75, 100),
                     expand = expansion(mult = c(0, 0))) +
  labs(x = NULL, y = "Share of pool (%)") +
  theme_fig() +
  theme(legend.position = "none", axis.text = element_text(size = 7.5),
        axis.title = element_text(size = 8.5),
        plot.margin = margin(2, 2, 2, 2))

## ---- panels b/c ---------------------------------------------------------------
BURDEN_ORD <- c("hearing_loss", "nasopharynx_cancer", "thyroid_cancer",
                "oral_cancer", "other_pharynx_cancer", "otitis_media",
                "larynx_cancer")
ATT_ORD <- c("osa", "crs_polyps", "allergic_rhinitis", "cochlear_implant",
             "tinnitus", "vertigo", "cholesteatoma")

## Panel b: dumbbell forest (burden tier).
# Redesign 2026-11-12 (chart-type quota, SKILL section 1.3): panel b is a
# dumbbell-forest / table hybrid (SKILL section 2: dumbbell for two-endpoint
# change, forest for aligned estimates; V7 aligned numeric column), NOT a
# line chart. One row per cause, ordered by 2020-24 window share; open dot =
# 1995-99 window share, filled dot = 2020-24 window share, endpoint values
# printed at the dots; right-hand column = percentage-point change (pp).
# Otitis media carries its window-counts note under its pp value.
b_first <- w %>% filter(area %in% BURDEN, win == "1995-99") %>%
  select(area, s_first = share)
b_last <- w %>% filter(area %in% BURDEN, win == "2020-24") %>%
  select(area, s_last = share)
bdat <- data.frame(area = BURDEN_ORD, stringsAsFactors = FALSE) %>%
  left_join(b_first, by = "area") %>% left_join(b_last, by = "area") %>%
  mutate(pp = s_last - s_first,
         y = rev(seq_along(BURDEN_ORD)),
         lab_first = sprintf("%.1f", s_first),
         lab_last = sprintf("%.1f", s_last),
         x_first_lab = ifelse(s_first >= s_last, s_first + 0.9, s_first - 0.9),
         hj_first = ifelse(s_first >= s_last, 0, 1),
         x_last_lab = ifelse(s_last >= s_first, s_last + 0.9, s_last - 0.9),
         hj_last = ifelse(s_last >= s_first, 0, 1),
         pp_txt = sprintf("%+.1f pp", pp))
stopifnot(!anyNA(bdat$s_first), !anyNA(bdat$s_last),
          all(diff(bdat$s_last) < 0))  # rows ordered by 2020-24 share
PP_X <- 26.5
ord_y <- order(bdat$y)
pb <- ggplot(bdat) +
  geom_segment(aes(x = s_first, xend = s_last, y = y, yend = y,
                   colour = area), linewidth = 0.9, alpha = 0.55) +
  geom_point(aes(x = s_first, y = y, colour = area),
             shape = 21, fill = "white", size = 2.5, stroke = 0.8) +
  geom_point(aes(x = s_last, y = y, fill = area),
             shape = 21, colour = "white", size = 2.5, stroke = 0.4) +
  geom_text(aes(x = x_first_lab, y = y, label = lab_first, hjust = hj_first),
            size = 2.3, colour = COL$grey_txt) +
  geom_text(aes(x = x_last_lab, y = y, label = lab_last, hjust = hj_last),
            size = 2.3, colour = COL$grey_txt) +
  geom_text(aes(x = PP_X, y = y, label = pp_txt),
            hjust = 0, size = 2.4, colour = COL$grey_txt) +
  geom_text(data = bdat %>% filter(area == "otitis_media"),
            aes(x = PP_X, y = y - 0.37, label = "counts 2,229 \u2192 3,706"),
            hjust = 0, size = 1.85, colour = COL$grey_txt) +
  annotate("point", x = 0, y = 7.85, shape = 21, fill = "white",
           colour = COL$grey_txt, size = 2.2) +
  annotate("text", x = 0.8, y = 7.85, label = "1995\u201399", hjust = 0,
           size = 2.3, colour = COL$grey_txt) +
  annotate("point", x = 8.6, y = 7.85, shape = 21, fill = COL$grey_txt,
           colour = COL$grey_txt, size = 2.2) +
  annotate("text", x = 9.4, y = 7.85, label = "2020\u201324", hjust = 0,
           size = 2.3, colour = COL$grey_txt) +
  annotate("text", x = PP_X, y = 7.85, label = "\u0394 pp", hjust = 0,
           size = 2.3, colour = COL$grey_txt) +
  scale_colour_manual(values = AREA_COL, guide = "none") +
  scale_fill_manual(values = AREA_COL, guide = "none") +
  scale_y_continuous(breaks = bdat$y[ord_y],
                     labels = LAB[bdat$area[ord_y]],
                     limits = c(0.4, 8.2)) +
  scale_x_continuous(breaks = c(0, 5, 10, 15, 20),
                     limits = c(-2.5, 40)) +
  labs(x = "Share (%)", y = NULL) +
  theme_fig() +
  theme(legend.position = "none", axis.text = element_text(size = 7.5),
        axis.title = element_text(size = 8.5),
        panel.grid.major.x = element_line(colour = "grey93",
                                          linewidth = 0.3),
        plot.margin = margin(2, 2, 2, 2))

## Panel c: area-filled sparkline facets (attention tier).
# Redesign 2026-11-12: the yearly share trace is drawn as a filled area
# (moderate alpha) with a heavier top edge, endpoint dots at the first/last
# window positions and the window-share labels at the ends - an area
# sparkline, not a bare line chart. OSA plateau phrase and the CRS asterisk
# (in LAB) are unchanged.
facet_area_plot <- function(areas_ordered, extra_labels = NULL,
                            drop_last = character(0)) {
  dd <- d %>% filter(area %in% areas_ordered)
  ww <- w %>% filter(area %in% areas_ordered)
  dd$area <- factor(dd$area, levels = areas_ordered)
  ww$area <- factor(ww$area, levels = areas_ordered)
  eps <- ww %>% filter(win %in% c("1995-99", "2020-24"))
  ends <- eps %>%
    filter(!(area %in% drop_last & win == "2020-24")) %>%
    mutate(txt = sprintf("%.1f", share),
           hj = ifelse(win == "1995-99", -0.25, 1.25))
  ggplot() +
    geom_area(data = dd, aes(year, share, fill = area), alpha = 0.45) +
    geom_line(data = dd, aes(year, share, colour = area), linewidth = 0.6) +
    geom_point(data = eps, aes(x, share, colour = area), size = 1.4) +
    geom_text(data = ends, aes(x, share, label = txt, hjust = hj),
              vjust = -0.6, size = 2.3, colour = COL$grey_txt) +
    geom_text(data = extra_labels,
              aes(x, y, label = txt, hjust = hj),
              size = 2.3, colour = COL$grey_txt) +
    facet_wrap(~ area, ncol = 1, scales = "free_y",
               labeller = labeller(area = LAB)) +
    scale_fill_manual(values = AREA_COL, guide = "none") +
    scale_colour_manual(values = AREA_COL, guide = "none") +
    scale_x_continuous(breaks = c(1995, 2005, 2015, 2024)) +
    scale_y_continuous(breaks = scales::breaks_pretty(n = 2),
                       expand = expansion(mult = c(0.04, 0.6))) +
    labs(x = "Year", y = "Share (%)") +
    theme_fig() +
    theme(legend.position = "none", axis.text = element_text(size = 7.5),
          axis.title = element_text(size = 8.5),
          strip.text = element_text(size = 8),
          panel.spacing.y = unit(3.2, "mm"))
}

ann_c <- data.frame(area = factor("osa", levels = ATT_ORD),
                    x = 2024, y = 15.4, txt = "\u224813% since 2005\u201309",
                    hj = 1)

pc <- facet_area_plot(ATT_ORD, extra_labels = ann_c, drop_last = "osa")

## ---- assemble -----------------------------------------------------------------
fig <- (pa / (pb | pc)) +
  plot_layout(heights = c(1.12, 1)) +
  plot_annotation(tag_levels = "a") &
  theme(plot.tag = element_text(size = 12, face = "bold", family = "Arial"))

save_fig(fig, "figures/fig2", width_mm = 180, height_mm = 225)
cat("saved figures/fig2.pdf + figures/fig2.png\n")

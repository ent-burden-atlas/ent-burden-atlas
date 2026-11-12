#!/usr/bin/env Rscript
# Fig 3 (main) — Yearly counts and shares, full detail, 1995-2024.
# Conclusions carried: (a) the complete 14-area x 30-year count matrix behind
#   Fig 2, log-scaled, burden tier above attention tier; (b) at yearly
#   resolution the five cancer areas' shares climb across the period
#   (combined 31.2% of the pool in 1995 -> 41.1% in 2024).
# Source (frozen): data_l1/l1_counts_by_year.csv (420 rows; Europe PMC
#   hitCounts under the frozen primary queries).
# IRON RULE: every number from the frozen file; stopifnot throughout.
source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages({ library(patchwork); library(colorspace) })

ROOT <- "~/workspace/ent-attention-burden"
BURDEN <- c("otitis_media","hearing_loss","larynx_cancer","oral_cancer",
            "nasopharynx_cancer","other_pharynx_cancer","thyroid_cancer")
ATT <- c("osa","crs_polyps","cochlear_implant","allergic_rhinitis",
         "tinnitus","vertigo","cholesteatoma")
ROWS <- c(BURDEN, ATT)
CANCERS <- c("larynx_cancer","oral_cancer","nasopharynx_cancer",
             "other_pharynx_cancer","thyroid_cancer")
LAB <- c(hearing_loss="Hearing loss", otitis_media="Otitis media",
         nasopharynx_cancer="Nasopharyngeal cancer",
         thyroid_cancer="Thyroid cancer", oral_cancer="Oral cancer",
         other_pharynx_cancer="Other pharyngeal cancer",
         larynx_cancer="Laryngeal cancer",
         osa="Obstructive sleep apnoea", crs_polyps="CRS / polyps",
         allergic_rhinitis="Allergic rhinitis",
         cochlear_implant="Cochlear implant", tinnitus="Tinnitus",
         vertigo="Vertigo", cholesteatoma="Cholesteatoma")
# Burden tier: shared CCOL hex values of Figs 2-4 (paper-wide). Attention
# tier: the desaturated AREA_COL hues of Fig 2, reproduced exactly.
CCOL <- c(otitis_media="#4DBBD5", hearing_loss="#E64B35",
          larynx_cancer="#8491B4", oral_cancer="#3C5488",
          nasopharynx_cancer="#DC0000", other_pharynx_cancer="#7E6148",
          thyroid_cancer="#8FAE94")
base <- pal_cat(12)
AREA_COL <- c(
  hearing_loss         = CCOL[["hearing_loss"]],
  otitis_media         = CCOL[["otitis_media"]],
  nasopharynx_cancer   = CCOL[["nasopharynx_cancer"]],
  oral_cancer          = CCOL[["oral_cancer"]],
  thyroid_cancer       = CCOL[["thyroid_cancer"]],
  other_pharynx_cancer = CCOL[["other_pharynx_cancer"]],
  larynx_cancer        = CCOL[["larynx_cancer"]],
  osa                  = desaturate(base[6], 0.25),
  crs_polyps           = base[8],
  cochlear_implant     = desaturate(base[6], 0.55),
  allergic_rhinitis    = lighten(base[5], 0.3),
  tinnitus             = base[12],
  vertigo              = desaturate(base[2], 0.55),
  cholesteatoma        = base[10])
SZ_TICK <- 7; SZ_LAB <- 7.5
near <- function(x, target, tol) abs(x - target) <= tol

## ---- data + assertions ---------------------------------------------------------
d <- read.csv(file.path(ROOT,"data_l1/l1_counts_by_year.csv"),
              stringsAsFactors=FALSE)
stopifnot(nrow(d)==420, setequal(unique(d$area), ROWS),
          setequal(unique(d$year), 1995:2024),
          all(table(d$area)==30))
win <- function(y0, y1) sum(d$count[d$year>=y0 & d$year<=y1])
stopifnot(win(1995,1999)==26544, win(2020,2024)==128117)
pool_y <- tapply(d$count, d$year, sum)
d$share <- d$count / pool_y[as.character(d$year)] * 100
five_y <- tapply(d$count[d$area %in% CANCERS], d$year[d$area %in% CANCERS], sum)
five_share <- five_y / pool_y * 100
win5 <- sum(d$count[d$area %in% CANCERS & d$year<=1999]) / 26544 * 100
# yearly 1995 five-cancer share consistent with the 1995-99 window share;
# 2024 yearly value printed from file (used in panel b and the caption).
stopifnot(near(win5, 32.06, 0.1),
          near(unname(five_share["1995"]), win5, 1.5),
          near(unname(five_share["2024"]), 41.10, 0.15))
cat(sprintf("five-cancer yearly share: 1995 = %.1f%%, 2024 = %.1f%% (window 1995-99 = %.1f%%)\n",
            five_share["1995"], five_share["2024"], win5))

## ---- panel a: count heatmap ------------------------------------------------------
d$area <- factor(d$area, levels=rev(ROWS))
d$lg <- log10(d$count)
lab_a <- data.frame(area=factor(ROWS, levels=rev(ROWS)),
                    name=LAB[ROWS],
                    col=AREA_COL[ROWS], stringsAsFactors=FALSE)
edge <- d[d$year %in% c(1995, 2024), ]
edge$txt <- sprintf("%d", edge$count)
edge$tcol <- ifelse(edge$lg >= 2.7, "white", "#333333")
pa <- ggplot(d, aes(year, area)) +
  geom_tile(aes(fill=lg), colour="white", linewidth=0.25) +
  geom_text(data=lab_a, aes(x=1994.35, y=area, label=name, colour=col),
            hjust=1, inherit.aes=FALSE, size=SZ_LAB/2.85) +
  geom_text(data=edge, aes(year, area, label=txt, colour=tcol),
            inherit.aes=FALSE, size=5/2.85) +
  scale_colour_identity() +
  scale_fill_gradient(low="#EDF2F5", high=COL$disease2,
                      name="Count (log10)") +
  scale_x_continuous(breaks=c(1995,2000,2005,2010,2015,2020,2024),
                     expand=c(0,0)) +
  labs(x=NULL, y=NULL) +
  coord_cartesian(xlim=c(1994.3, 2024.55), clip="off") +
  theme_fig(9) + theme(axis.text.y=element_blank(), axis.ticks.y=element_blank(),
                       axis.line.y=element_blank(),
                       axis.text.x=element_text(size=SZ_TICK),
                       panel.grid.major.y=element_blank(),
                       legend.position="bottom", legend.justification="left",
                       legend.title=element_text(size=SZ_TICK),
                       legend.text=element_text(size=SZ_TICK),
                       legend.key.height=unit(3, "mm"),
                       legend.key.width=unit(9, "mm"),
                       plot.margin=margin(4, 4, 2, 92))

## ---- panel b: yearly shares, five cancers — area-filled sparkline facets -----------
# Per the v3 bar+line quota, panel b is NOT line traces: one filled-area
# sparkline facet per cancer (share of the whole 14-area pool, %), free y
# scale per facet, endpoint dots with first/last values labelled.
dc <- d[d$area %in% CANCERS, ]
dc$area <- factor(dc$area, levels=CANCERS)
SHORT <- c(larynx_cancer="Larynx", oral_cancer="Oral",
           nasopharynx_cancer="Nasopharynx",
           other_pharynx_cancer="Other pharynx", thyroid_cancer="Thyroid")
ends <- dc[dc$year %in% c(1995, 2024), ]
rng <- tapply(dc$share, dc$area, function(x) max(x) - min(x))
ends$ylab <- ends$share + 0.16 * rng[as.character(ends$area)] + 0.15
ends$txt <- sprintf("%.1f%%", ends$share)
ends$hj <- ifelse(ends$year==1995, 0, 1)
comb_df <- data.frame(area=factor("oral_cancer", levels=CANCERS),
                      year=1995.3, share=11.9,
                      txt=sprintf("Combined: %.1f%% \u2192 %.1f%%",
                                  five_share["1995"], five_share["2024"]),
                      stringsAsFactors=FALSE)
pb <- ggplot(dc, aes(year, share)) +
  geom_area(aes(fill=area), alpha=0.72, colour=NA) +
  geom_line(aes(colour=area), linewidth=0.7) +
  geom_point(data=ends, aes(year, share, colour=area), size=1.6,
             fill="white", shape=21, stroke=0.7) +
  geom_text(data=ends, aes(year, ylab, label=txt, hjust=hj),
            size=SZ_LAB/2.85, colour=COL$grey_txt) +
  geom_text(data=comb_df, aes(year, share, label=txt), hjust=0,
            size=6.3/2.85, colour=COL$grey_ax) +
  scale_fill_manual(values=CCOL, guide="none") +
  scale_colour_manual(values=CCOL, guide="none") +
  scale_x_continuous(breaks=c(1995, 2005, 2015, 2024)) +
  scale_y_continuous(expand=expansion(mult=c(0.01, 0.30))) +
  facet_wrap(~area, nrow=1, scales="free_y",
             labeller=labeller(area=SHORT)) +
  labs(x=NULL, y="Share of pool (%)") +
  coord_cartesian(clip="off") +
  theme_fig(9) + theme(legend.position="none",
                       axis.text=element_text(size=6.5),
                       axis.text.y=element_blank(), axis.ticks.y=element_blank(),
                       axis.line.y=element_blank(),
                       axis.title=element_text(size=8.5),
                       strip.text=element_text(size=8, face="bold"),
                       panel.grid.major.y=element_blank(),
                       panel.spacing=unit(3.5, "mm"),
                       plot.margin=margin(4, 4, 2, 92))

fig3 <- pa / pb + plot_layout(heights=c(94, 56)) +
  plot_annotation(tag_levels="a",
                  theme=theme(plot.tag=element_text(size=12, face="bold",
                                                    family="Arial")))
save_fig(fig3, file.path(ROOT,"figures/fig3"), width_mm=180, height_mm=150)
cat("fig3 done\n")

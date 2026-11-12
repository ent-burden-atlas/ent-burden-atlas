#!/usr/bin/env Rscript
# Fig S1 (supplementary) — Sensitivity full grids.
# REV2 (2026-11-12, light fix): panel-b percent labels moved from above/below
# the points (where they collided across adjacent rows in the dense negative
# cluster) to the outer side of each point, centred on its row; x-axis breaks
# respaced (-100/-25/0/+25/+100/+1000) so tick labels no longer touch. Data,
# assertions, panel a and every printed value are unchanged from rev1.
# Conclusions carried: (a) the two ABR sensitivity calibres in full: under the
#   prevalence calibre, hearing loss remains deeply negative (-1.82) but the
#   two smallest-burden causes cross zero (the prevalence pool is dominated
#   by hearing loss); the publication-window calibre (2020-23 counts) is
#   near-identical to the primary. (b) terminology sensitivity: primary vs
#   backup query directions agree for 12 of 15 rows; CRS reverses outright.
# Sources (frozen): data_l2/abr/abr_prevalence_sensitivity.csv,
#   abr_sensitivity_pub2020_2023.csv, abr_primary.csv (assertion reference);
#   data_l1/terminology_sensitivity.csv (15 rows).
# IRON RULE: every number from the frozen files; stopifnot throughout.
source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages({ library(patchwork); library(tidyr) })

ROOT <- "~/workspace/ent-attention-burden"
PERIODS <- c("1995-1999","2000-2004","2005-2009","2010-2014","2015-2019","2020-2024")
PER_LAB <- c("1995-99","2000-04","2005-09","2010-14","2015-19","2020-24")
CAUSES <- c("otitis_media","hearing_loss","larynx_cancer","oral_cancer",
            "nasopharynx_cancer","other_pharynx_cancer","thyroid_cancer")
LAB <- c(otitis_media="Otitis media", hearing_loss="Hearing loss",
         larynx_cancer="Larynx cancer", oral_cancer="Oral cancer",
         nasopharynx_cancer="Nasopharynx cancer",
         other_pharynx_cancer="Other pharynx cancer",
         thyroid_cancer="Thyroid cancer")
SZ_TICK <- 7; SZ_LAB <- 7.5; SZ_VAL <- 6.5
near <- function(x, target, tol) abs(x - target) <= tol
get_v <- function(d, a, p) d$log2_abr[d$area==a & d$period==p]

## ---- data + assertions -----------------------------------------------------------
pri <- read.csv(file.path(ROOT,"data_l2/abr/abr_primary.csv"), stringsAsFactors=FALSE)
prv <- read.csv(file.path(ROOT,"data_l2/abr/abr_prevalence_sensitivity.csv"),
                stringsAsFactors=FALSE)
sen <- read.csv(file.path(ROOT,"data_l2/abr/abr_sensitivity_pub2020_2023.csv"),
                stringsAsFactors=FALSE)
stopifnot(nrow(pri)==42, nrow(prv)==42, nrow(sen)==42,
          setequal(unique(prv$area), CAUSES), setequal(unique(sen$area), CAUSES))
stopifnot(near(get_v(prv,"hearing_loss","2020-2024"), -1.82, 0.03))
# publication-window sensitivity vs primary: identical outside the last
# period (recomputed cell by cell), last-period signs unchanged.
mg <- merge(pri, sen, by=c("area","period"), suffixes=c("_pri","_sen"))
early <- mg[mg$period!="2020-2024", ]
lastm <- mg[mg$period=="2020-2024", ]
stopifnot(nrow(early)==35, nrow(lastm)==7,
          all(abs(early$log2_abr_pri - early$log2_abr_sen) < 1e-9),
          all(sign(lastm$log2_abr_pri)==sign(lastm$log2_abr_sen)),
          all(abs(lastm$log2_abr_pri - lastm$log2_abr_sen) < 0.1))
# prevalence calibre: exactly otitis media and larynx cancer change sign
# vs the primary in the last period.
sgn <- sapply(CAUSES, function(a)
  sign(get_v(prv,a,"2020-2024")) != sign(get_v(pri,a,"2020-2024")))
stopifnot(setequal(names(sgn)[sgn], c("otitis_media","larynx_cancer")))

## ---- panel a: two aligned ABR grids, shared diverging scale -----------------------
ord_a <- CAUSES[order(sapply(CAUSES, function(a) get_v(pri,a,"2020-2024")))]
mk <- function(d, cal) data.frame(area=d$area, period=d$period,
                                  calibre=cal, v=d$log2_abr,
                                  stringsAsFactors=FALSE)
ga <- rbind(mk(prv, "Prevalence calibre"),
            mk(sen, "Publication window 2020\u201323"))
ga$area <- factor(ga$area, levels=ord_a)
ga$period <- factor(ga$period, levels=PERIODS)
ga$calibre <- factor(ga$calibre,
                     levels=c("Prevalence calibre","Publication window 2020\u201323"))
ga$txt <- sprintf("%+.2f", ga$v)
ga$tcol <- ifelse(abs(ga$v) > 3.4, "white", "#333333")
pa <- ggplot(ga, aes(period, area)) +
  geom_tile(aes(fill=v), colour="white", linewidth=0.4) +
  geom_text(aes(label=txt, colour=tcol), size=SZ_VAL/2.85) +
  scale_colour_identity() +
  scale_fill_gradient2(low=COL$down, mid="white", high=COL$up, midpoint=0,
                       limits=c(-10, 10), breaks=c(-5, 0, 5),
                       name="log2 ABR") +
  scale_x_discrete(labels=PER_LAB) +
  scale_y_discrete(labels=LAB) +
  facet_wrap(~calibre, nrow=1) +
  labs(x=NULL, y=NULL) +
  theme_fig(9) + theme(axis.text=element_text(size=SZ_TICK),
                       axis.text.x=element_text(size=6.5, angle=30, hjust=1),
                       strip.text=element_text(size=8.5, face="bold"),
                       panel.grid.major.y=element_blank(),
                       legend.position="right",
                       legend.title=element_text(size=SZ_TICK),
                       legend.text=element_text(size=SZ_TICK),
                       legend.key.height=unit(9, "mm"),
                       legend.key.width=unit(3.2, "mm"),
                       plot.margin=margin(4, 4, 2, 2))

## ---- panel b: terminology dumbbells ------------------------------------------------
ts <- read.csv(file.path(ROOT,"data_l1/terminology_sensitivity.csv"),
               stringsAsFactors=FALSE)
stopifnot(nrow(ts)==15,
          sum(ts$directions_agree=="yes")==12,
          sum(ts$directions_agree=="NO")==3,
          setequal(ts$area[ts$directions_agree=="NO"],
                   c("crs_polyps","cochlear_implant","tinnitus")),
          near(ts$primary_rel_change_pct[ts$area=="crs_polyps"], -26.6, 1),
          near(ts$backup_rel_change_pct[ts$area=="crs_polyps"],  251.0, 1))
LABB <- c(hearing_loss="Hearing loss", otitis_media="Otitis media",
          nasopharynx_cancer="Nasopharyngeal cancer",
          thyroid_cancer="Thyroid cancer", oral_cancer="Oral cancer",
          other_pharynx_cancer="Other pharyngeal cancer",
          larynx_cancer="Laryngeal cancer",
          osa="Obstructive sleep apnoea", crs_polyps="CRS / polyps",
          allergic_rhinitis="Allergic rhinitis",
          cochlear_implant="Cochlear implant", tinnitus="Tinnitus",
          vertigo="Vertigo", cholesteatoma="Cholesteatoma",
          five_cancers_combined="Five cancers combined")
sxt <- function(x) sign(x) * log10(1 + abs(x))
areas_b <- ts$area[ts$area!="five_cancers_combined"]
ord_b <- areas_b[order(-ts$primary_rel_change_pct[match(areas_b, ts$area)])]
disp_b <- c("five_cancers_combined", ord_b)          # top -> bottom
ts$y <- length(disp_b) - match(ts$area, disp_b) + 1  # combined row on top
ts$xp <- sxt(ts$primary_rel_change_pct)
ts$xb <- sxt(ts$backup_rel_change_pct)
ts$disagree <- ts$directions_agree=="NO"
lab_b <- data.frame(y=ts$y, name=LABB[ts$area], disagree=ts$disagree,
                    stringsAsFactors=FALSE)
pts <- rbind(data.frame(y=ts$y, x=ts$xp, kind="Primary query",
                        val=ts$primary_rel_change_pct),
             data.frame(y=ts$y, x=ts$xb, kind="Backup query",
                        val=ts$backup_rel_change_pct))
pts$kind <- factor(pts$kind, levels=c("Primary query","Backup query"))
# rev2: label placement — each percent label on the outer side of its own
# point (away from the dumbbell's other end), vertically centred on the row.
lab_pts <- rbind(
  data.frame(y=ts$y, x=ts$xp, val=ts$primary_rel_change_pct, other=ts$xb),
  data.frame(y=ts$y, x=ts$xb, val=ts$backup_rel_change_pct, other=ts$xp))
lab_pts$side <- ifelse(lab_pts$x >= lab_pts$other, 1, -1)
lab_pts$lx <- lab_pts$x + lab_pts$side * 0.07
lab_pts$hj <- ifelse(lab_pts$side > 0, 0, 1)
lab_pts$txt <- sprintf("%+.0f%%", lab_pts$val)
flag <- data.frame(y=ts$y[ts$disagree], x=sxt(1000)+0.28, label="differs",
                   stringsAsFactors=FALSE)
brk <- c(-100,-25,0,25,100,1000)
pb <- ggplot() +
  annotate("segment", x=-2.62, xend=sxt(1000)+0.62,
           y=length(disp_b)-0.5, yend=length(disp_b)-0.5,
           colour="#CCCCCC", linewidth=0.4) +
  geom_vline(xintercept=0, colour="#333333", linewidth=0.6) +
  geom_segment(data=ts, aes(x=xp, xend=xb, y=y, yend=y),
               colour="#BFBFBF", linewidth=0.7) +
  geom_point(data=pts, aes(x, y, fill=kind, colour=kind),
             shape=21, size=2.6, stroke=0.7) +
  geom_text(data=lab_pts,
            aes(lx, y, label=txt, hjust=hj),
            vjust=0.5, size=5.5/2.85, colour=COL$grey_ax) +
  geom_text(data=lab_b[!lab_b$disagree,], aes(x=-2.68, y=y, label=name),
            hjust=1, size=SZ_LAB/2.85, colour=COL$grey_txt,
            inherit.aes=FALSE) +
  geom_text(data=lab_b[lab_b$disagree,], aes(x=-2.68, y=y, label=name),
            hjust=1, size=SZ_LAB/2.85, fontface="bold", colour=COL$up,
            inherit.aes=FALSE) +
  geom_text(data=flag, aes(x=x, y=y, label=label),
            hjust=0, size=SZ_LAB/2.85, fontface="bold", colour=COL$up,
            inherit.aes=FALSE) +
  scale_fill_manual(values=c("Primary query"=COL$disease2,
                             "Backup query"="white"), name=NULL) +
  scale_colour_manual(values=c("Primary query"="white",
                               "Backup query"=COL$disease2), name=NULL,
                      guide="none") +
  scale_x_continuous(breaks=sxt(brk),
                     labels=c("-100%","-25%","0","+25%","+100%",
                              "+1000%")) +
  labs(x="Relative share change, 1995\u201399 \u2192 2020\u201324 (signed log scale)",
       y=NULL) +
  coord_cartesian(xlim=c(-2.62, sxt(1000)+0.62), ylim=c(0.35, length(disp_b)+0.75),
                  clip="off") +
  theme_fig(9) + theme(axis.text.y=element_blank(), axis.ticks.y=element_blank(),
                       axis.line.y=element_blank(),
                       axis.text.x=element_text(size=SZ_TICK),
                       axis.title=element_text(size=8.5),
                       panel.grid.major.y=element_blank(),
                       panel.grid.major.x=element_line(colour="#EEEEEE",
                                                       linewidth=0.3),
                       legend.position="bottom", legend.justification="left",
                       legend.text=element_text(size=SZ_TICK),
                       legend.key.size=unit(3.2, "mm"),
                       plot.margin=margin(4, 16, 2, 92))

figS1 <- pa / pb + plot_layout(heights=c(62, 96)) +
  plot_annotation(tag_levels="a",
                  theme=theme(plot.tag=element_text(size=12, face="bold",
                                                    family="Arial")))
save_fig(figS1, file.path(ROOT,"figures/figS1_rev2"), width_mm=180, height_mm=158)
cat("figS1 done\n")

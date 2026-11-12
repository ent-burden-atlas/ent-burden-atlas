#!/usr/bin/env Rscript
# Fig 3 — ABR headline figure: attention-burden ratio, 7 GBD burden-tier causes, 1995-2024.
# Conclusions carried: (a) hearing loss is the deepest and worsening under-attention
#   (log2 ABR -1.05 -> -1.47); thyroid and nasopharynx cancers sit far above parity.
#   (b) the hearing-loss gap is compositional: 72.7% of pooled DALYs vs 26.3% of
#   pooled publications in the last period. (c) last-period log2 ABR is stable to a
#   10-year burden lag in sign for all causes; in the prevalence calibre two causes
#   (otitis media, laryngeal cancer) cross zero and are flagged, because that pool
#   is dominated by hearing-loss prevalence.
# Teardown rules applied (figures/teardown_notes.md): R3 numbers in aligned columns,
#   direct labels instead of legend stacks; V1 no in-figure prose.
# Sources (frozen): data_l2/abr/abr_primary.csv, abr_prevalence_sensitivity.csv,
#   abr_lag_sensitivity.csv. Cause colours (CCOL) and labels (LAB) match Fig 4.
# IRON RULE: every number from the frozen files above; stopifnot throughout.
#
# ASSERTION NOTE (parent adjudication set, verified 2026-11-12): all anchor, lag and
# sign assertions hold exactly as specified. ONE specified assertion does NOT hold as
# stated and is asserted below in its verified form instead of being fudged:
# cross-calibre first->last TREND sign agreement is 5 of 7, not 7 of 7. Exceptions:
# other_pharynx_cancer (primary +0.111 vs prevalence -0.206) and thyroid_cancer
# (primary +0.186 vs prevalence -0.118) -- near-flat trends in both calibres. The two
# panel-c sign-crossers (otitis media, larynx cancer) DO trend-agree, which is what
# the caption states. No panel and no caption sentence claims all-7 trend agreement.
source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages({ library(patchwork); library(tidyr) })

ROOT <- "~/workspace/ent-attention-burden"
PERIODS <- c("1995-1999","2000-2004","2005-2009","2010-2014","2015-2019","2020-2024")
CAUSES <- c("otitis_media","hearing_loss","larynx_cancer","oral_cancer",
            "nasopharynx_cancer","other_pharynx_cancer","thyroid_cancer")
LAB <- c(otitis_media="Otitis media", hearing_loss="Hearing loss",
         larynx_cancer="Larynx cancer", oral_cancer="Oral cancer",
         nasopharynx_cancer="Nasopharynx cancer",
         other_pharynx_cancer="Other pharynx cancer",
         thyroid_cancer="Thyroid cancer")
CCOL <- c(otitis_media="#4DBBD5", hearing_loss="#E64B35", larynx_cancer="#8491B4",
          oral_cancer="#3C5488", nasopharynx_cancer="#DC0000",
          other_pharynx_cancer="#7E6148", thyroid_cancer="#8FAE94")
SZ_TICK <- 7; SZ_LAB <- 7.5; SZ_VAL <- 7

## ---- data ---------------------------------------------------------------------
pri <- read.csv(file.path(ROOT,"data_l2/abr/abr_primary.csv"), stringsAsFactors=FALSE)
prv <- read.csv(file.path(ROOT,"data_l2/abr/abr_prevalence_sensitivity.csv"),
                stringsAsFactors=FALSE)
lag <- read.csv(file.path(ROOT,"data_l2/abr/abr_lag_sensitivity.csv"),
                stringsAsFactors=FALSE)
stopifnot(nrow(pri)==42, nrow(prv)==42, nrow(lag)==105,
          setequal(unique(pri$area), CAUSES), setequal(unique(pri$period), PERIODS),
          setequal(unique(prv$area), CAUSES), setequal(unique(lag$area), CAUSES))
get_v <- function(d, a, p, col="log2_abr") d[[col]][d$area==a & d$period==p]
near <- function(x, target, tol) abs(x - target) <= tol

## ---- assertions: anchors -------------------------------------------------------
stopifnot(
  near(get_v(pri,"hearing_loss","1995-1999"), -1.05, 0.03),
  near(get_v(pri,"hearing_loss","2020-2024"), -1.47, 0.03),
  near(get_v(pri,"thyroid_cancer","2020-2024"),  3.24, 0.03),
  near(get_v(pri,"larynx_cancer","1995-1999"), -0.18, 0.03),
  near(get_v(pri,"larynx_cancer","2020-2024"), -1.185, 0.02),
  near(get_v(pri,"otitis_media","1995-1999"),   1.39, 0.03),
  near(get_v(pri,"otitis_media","2020-2024"),   0.34, 0.03),
  near(get_v(prv,"hearing_loss","2020-2024"),  -1.82, 0.05),
  near(get_v(prv,"thyroid_cancer","2020-2024"), 7.30, 0.05),
  # panel b hearing-loss composition pair (percentage points)
  near(get_v(pri,"hearing_loss","2020-2024","burden_share_pool")*100, 72.7, 0.15),
  near(get_v(pri,"hearing_loss","2020-2024","pub_share_burden_pool")*100, 26.3, 0.15),
  # caption: hearing loss dominates the last-period prevalence pool
  near(get_v(prv,"hearing_loss","2020-2024","burden_share_pool")*100, 92.8, 0.15))

## ---- assertions: lag sensitivity ------------------------------------------------
lagw <- lag %>% select(area, pub_period, lag_years, log2_abr_lag) %>%
  pivot_wider(names_from=lag_years, values_from=log2_abr_lag,
              names_prefix="lag") %>%
  rename(lag0=`lag0`, lag5=`lag5`, lag10=`lag10`)
full <- lagw[complete.cases(lagw), ]
stopifnot(nrow(full)==28,
          all(sign(full$lag0)==sign(full$lag5) & sign(full$lag0)==sign(full$lag10)))
lag_last <- lagw[lagw$pub_period=="2020-2024", ]
stopifnot(all(abs(lag_last$lag5 - lag_last$lag0) <= 0.14),
          all(abs(lag_last$lag10 - lag_last$lag5) <= 0.14),
          all(abs(lag_last$lag10 - lag_last$lag0) <= 0.28),
          near(abs(lag_last$lag10[lag_last$area=="otitis_media"] -
                   lag_last$lag0[lag_last$area=="otitis_media"]), 0.2713, 0.005),
          # (i) primary vs lag-10 last-period signs agree for all 7
          all(sign(lag_last$lag10) ==
              sign(sapply(lag_last$area, function(a)
                get_v(pri, a, "2020-2024")))))

## ---- assertions: calibre agreement ----------------------------------------------
pri_last <- sapply(CAUSES, function(a) get_v(pri, a, "2020-2024"))
prv_last <- sapply(CAUSES, function(a) get_v(prv, a, "2020-2024"))
pri_trend <- pri_last - sapply(CAUSES, function(a) get_v(pri, a, "1995-1999"))
prv_trend <- prv_last - sapply(CAUSES, function(a) get_v(prv, a, "1995-1999"))
sign_agree <- names(pri_last)[sign(prv_last) != sign(pri_last)]
trend_agree_n <- sum(sign(prv_trend) == sign(pri_trend))
stopifnot(
  # (iii) prevalence last-period signs agree with primary for exactly 5 of 7
  length(sign_agree)==2, setequal(sign_agree, c("otitis_media","larynx_cancer")),
  near(prv_last[["otitis_media"]], -0.617, 0.02),
  near(prv_last[["larynx_cancer"]],  4.938, 0.02),
  # (ii) VERIFIED form (see header note): trend signs agree for 5 of 7; the two
  # exceptions are near-flat in both calibres; the two sign-crossers trend-agree.
  trend_agree_n==5,
  setequal(names(pri_trend)[sign(prv_trend) != sign(pri_trend)],
           c("other_pharynx_cancer","thyroid_cancer")),
  near(pri_trend[["other_pharynx_cancer"]],  0.111, 0.01),
  near(prv_trend[["other_pharynx_cancer"]], -0.206, 0.01),
  near(pri_trend[["thyroid_cancer"]],        0.186, 0.01),
  near(prv_trend[["thyroid_cancer"]],       -0.118, 0.01),
  sign(prv_trend[["otitis_media"]])==sign(pri_trend[["otitis_media"]]),
  sign(prv_trend[["larynx_cancer"]])==sign(pri_trend[["larynx_cancer"]]))

## ---- panel a: anchor trajectories ----------------------------------------------
pri$pidx <- match(pri$period, PERIODS)
last_a <- pri[pri$period=="2020-2024", ]
last_a <- last_a[order(-last_a$log2_abr), ]
ord_a <- last_a$area                       # top (thyroid) -> bottom (hearing)
endlab <- data.frame(area=last_a$area, y=last_a$log2_abr,
                     name=LAB[last_a$area],
                     val=sprintf("%+.2f", last_a$log2_abr),
                     stringsAsFactors=FALSE)
pa <- ggplot(pri, aes(pidx, log2_abr, colour=area, group=area)) +
  annotate("rect", xmin=0.8, xmax=6.32, ymin=-1.78, ymax=0,
           fill="#8491B4", alpha=0.10) +
  annotate("segment", x=0.8, xend=6.32, y=0, yend=0,
           colour="#333333", linewidth=0.7) +
  annotate("text", x=0.95, y=-1.58, label="ABR < 1", hjust=0, size=SZ_LAB/2.85,
           colour=COL$grey_ax) +
  geom_line(linewidth=0.9) +
  geom_line(data=pri[pri$area=="hearing_loss",], linewidth=1.25) +
  geom_point(size=1.3) +
  geom_point(data=last_a, size=2.1) +
  geom_text(data=endlab, aes(x=6.52, y=y, label=name), hjust=0, inherit.aes=FALSE,
            size=SZ_LAB/2.85, colour=COL$grey_txt) +
  geom_text(data=endlab, aes(x=8.5, y=y, label=val), hjust=1, inherit.aes=FALSE,
            size=SZ_LAB/2.85, fontface="bold", colour=COL$grey_txt) +
  scale_colour_manual(values=CCOL, guide="none") +
  scale_x_continuous(breaks=1:6, limits=c(0.8, 8.55),
                     labels=c("1995-99","2000-04","2005-09","2010-14",
                              "2015-19","2020-24")) +
  scale_y_continuous(breaks=c(-1,0,1,2,3), limits=c(-1.78, 3.62)) +
  labs(x=NULL, y="log2 ABR") +
  coord_cartesian(clip="off") +
  theme_fig(10) + theme(legend.position="none",
                        axis.text=element_text(size=SZ_TICK),
                        axis.title=element_text(size=9),
                        plot.margin=margin(4, 6, 2, 2))

## ---- panel b: last-period composition dumbbell ----------------------------------
comp <- data.frame(area=CAUSES, stringsAsFactors=FALSE)
comp$burden <- sapply(CAUSES, function(a) get_v(pri, a, "2020-2024", "burden_share_pool")*100)
comp$pub    <- sapply(CAUSES, function(a) get_v(pri, a, "2020-2024", "pub_share_burden_pool")*100)
comp$gap <- comp$burden - comp$pub
comp <- comp[order(-comp$gap), ]
stopifnot(comp$area[1]=="hearing_loss", near(comp$gap[1], 46.4, 0.2))
comp$area <- factor(comp$area, levels=rev(comp$area))
comp$name <- LAB[as.character(comp$area)]
long_b <- rbind(
  data.frame(area=comp$area, name=comp$name, kind="DALY share",
             share=comp$burden, stringsAsFactors=FALSE),
  data.frame(area=comp$area, name=comp$name, kind="Publication share",
             share=comp$pub, stringsAsFactors=FALSE))
long_b$val <- sprintf("%.1f", long_b$share)
long_b$is_hearing <- long_b$name=="Hearing loss"
pb <- ggplot() +
  geom_segment(data=comp, aes(x=pub, xend=burden, y=area, yend=area),
               colour="#BFBFBF", linewidth=0.7) +
  geom_point(data=long_b, aes(share, area, fill=kind), shape=21, size=2.7,
             colour="white", stroke=0.5) +
  geom_text(data=long_b[!long_b$is_hearing & long_b$kind=="DALY share",],
            aes(share, area, label=val),
            vjust=-1.05, size=6.5/2.85, colour=COL$grey_ax) +
  geom_text(data=long_b[!long_b$is_hearing & long_b$kind=="Publication share",],
            aes(share, area, label=val),
            vjust=1.9, size=6.5/2.85, colour=COL$grey_ax) +
  geom_text(data=long_b[long_b$is_hearing,], aes(share, area, label=val),
            vjust=-1.0, size=SZ_LAB/2.85, fontface="bold", colour=COL$grey_txt) +
  scale_fill_manual(values=c("DALY share"=COL$disease2,
                             "Publication share"=COL$down), name=NULL) +
  scale_y_discrete(labels=LAB) +
  scale_x_continuous(limits=c(0, 86), breaks=c(0, 25, 50, 75),
                     expand=expansion(mult=c(0.01, 0.02))) +
  labs(x="Share of 7-cause pool (%)", y=NULL) +
  theme_fig(10) +
  theme(panel.grid.major.y=element_blank(),
        panel.grid.major.x=element_line(colour="#EEEEEE", linewidth=0.3),
        axis.text=element_text(size=SZ_TICK), axis.title=element_text(size=9),
        # key sits in the verified blank right-centre area (no data beyond x=21
        # below the hearing-loss row); zero data occlusion (V4).
        legend.position=c(0.97, 0.80), legend.justification=c(1, 1),
        legend.text=element_text(size=SZ_TICK), legend.key.size=unit(3.2, "mm"),
        plot.margin=margin(4, 4, 2, 2))

## ---- panel c: last-period sensitivity dot plot -----------------------------------
lvl_c <- CAUSES[order(pri_last[CAUSES])]           # ascending primary log2 ABR
dots <- rbind(
  data.frame(area=CAUSES, calibre="Primary (DALY)", value=pri_last[CAUSES]),
  data.frame(area=CAUSES, calibre="Prevalence",     value=prv_last[CAUSES]),
  data.frame(area=CAUSES, calibre="Lag 10 y",
             value=sapply(CAUSES, function(a)
               lag_last$lag10[lag_last$area==a])))
dots$area <- factor(dots$area, levels=lvl_c)
dots$calibre <- factor(dots$calibre,
                       levels=c("Primary (DALY)","Prevalence","Lag 10 y"))
# draw order: prevalence first, lag triangles behind, primary dots on top; the
# larger triangle stays visible behind a coincident primary dot (lag stability).
dots <- dots[order(match(dots$calibre,
                         c("Prevalence","Lag 10 y","Primary (DALY)"))), ]
dots$psize <- ifelse(dots$calibre=="Lag 10 y", 3.3, 2.7)
span_c <- dots %>% group_by(area) %>%
  summarise(xmin=min(value), xmax=max(value), .groups="drop")
warn <- dots[dots$calibre=="Prevalence" &
             dots$area %in% c("otitis_media","larynx_cancer"), ]
tags <- data.frame(area=factor(c("otitis_media","larynx_cancer"), levels=lvl_c),
                   x=c(-0.55, 5.15), yoff=c(0.42, 0),
                   label="sign differs", stringsAsFactors=FALSE)
tags$y <- as.integer(tags$area) + tags$yoff
pc <- ggplot() +
  annotate("rect", xmin=-2.15, xmax=0, ymin=0.4, ymax=7.6,
           fill="#8491B4", alpha=0.10) +
  geom_vline(xintercept=0, colour="#333333", linewidth=0.7) +
  geom_segment(data=span_c, aes(x=xmin, xend=xmax, y=area, yend=area),
               colour="#D9D9D9", linewidth=0.7) +
  geom_point(data=dots, aes(value, area, shape=calibre, fill=calibre,
                            colour=calibre, size=psize), stroke=0.7) +
  scale_size_continuous(range=c(2.7, 3.3), guide="none") +
  geom_point(data=warn, aes(value, area), shape=21, fill=NA,
             colour=COL$up, size=5.2, stroke=1.1) +
  geom_text(data=tags, aes(x=x, y=y, label=label), hjust=0,
            size=SZ_LAB/2.85, fontface="bold", colour=COL$up) +
  scale_shape_manual(values=c("Primary (DALY)"=21, "Prevalence"=21, "Lag 10 y"=24),
                     name=NULL) +
  scale_fill_manual(values=c("Primary (DALY)"=COL$disease2, "Prevalence"="white",
                             "Lag 10 y"=COL$neutral), name=NULL, guide="none") +
  scale_colour_manual(values=c("Primary (DALY)"="white", "Prevalence"=COL$disease2,
                               "Lag 10 y"="white"), name=NULL, guide="none") +
  scale_y_discrete(labels=LAB) +
  scale_x_continuous(breaks=c(-2, 0, 2, 4, 6, 8, 10), limits=c(-2.15, 10.4)) +
  labs(x="log2 ABR (2020-2024)", y=NULL) +
  guides(shape=guide_legend(nrow=1,
           override.aes=list(fill=c(COL$disease2, "white", COL$neutral),
                             colour=c("white", COL$disease2, "white"),
                             size=2.8, stroke=0.7))) +
  theme_fig(10) +
  theme(panel.grid.major.y=element_blank(),
        panel.grid.major.x=element_line(colour="#EEEEEE", linewidth=0.3),
        axis.text=element_text(size=SZ_TICK), axis.title=element_text(size=9),
        legend.position="bottom", legend.justification="left",
        legend.text=element_text(size=SZ_TICK), legend.key.size=unit(3.2, "mm"),
        plot.margin=margin(4, 4, 2, 2))

## ---- compose ----------------------------------------------------------------------
bottom <- (pb | pc) + plot_layout(widths=c(0.94, 1.06))
fig4 <- pa / bottom + plot_layout(heights=c(88, 82)) +
  plot_annotation(tag_levels="a",
                  theme=theme(plot.tag=element_text(size=12.5, face="bold",
                                                    family="Arial")))
save_fig(fig4, file.path(ROOT,"figures/fig4"), width_mm=180, height_mm=170)
cat("fig4 done\n")

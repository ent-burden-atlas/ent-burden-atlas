#!/usr/bin/env Rscript
# Fig 4 — Geography: double-centroid convergence, 7 GBD burden-tier causes, 1995–2024.
# Conclusions carried: (a) burden–research centroid distance shrank for all 7 causes
#   (otitis media most, −80%); nasopharynx cancer shows the one large last-step
#   rebound (978 -> 2,467 km; thyroid cancer also ticks up slightly, +82 km).
#   (b) both centroids moved, on a world basemap (country-centre approximation).
#   (c) LMIC first-author share rose 7.9% -> 39.8% (5.4% -> 17.9% excluding China).
# Teardown rules applied (figures/teardown_notes.md): R2 map = basemap only, data layer
#   is points + arrows; R3 direct labels, no legend stacks.
# Estimator (FREEZE v2, user ruling 2026-11-12): weighted mean centre of country
#   centres (weighted mean latitude; circular mean longitude); v1 chordal values
#   are archived and must NOT be used. See data_l3/geo/centroid/FREEZE_v2.md.
# Sources (frozen): data_l3/geo/centroid/double_centroid.csv (v2),
#   data_l3/geo/country_counts.csv x data_l3/geo/ref/country_reference.csv (is_lmic,
#   frozen World Bank snapshot 2026-11-12) for the sanctioned panel-c recompute ->
#   data_l3/geo/centroid/lmic_series_recomputed.csv.
# IRON RULE: every number from the frozen files above; stopifnot throughout.
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
# <=3 saturated anchors (red, navy, teal); remaining causes use desaturated variants.
CCOL <- c(otitis_media="#4DBBD5", hearing_loss="#E64B35", larynx_cancer="#8491B4",
          oral_cancer="#3C5488", nasopharynx_cancer="#DC0000",
          other_pharynx_cancer="#7E6148", thyroid_cancer="#8FAE94")
fmt_km <- function(x) formatC(round(x), format="d", big.mark=",")

## ---- data + assertions -------------------------------------------------------
dc <- read.csv(file.path(ROOT,"data_l3/geo/centroid/double_centroid.csv"),
               stringsAsFactors=FALSE)
stopifnot(nrow(dc)==42, setequal(unique(dc$area), CAUSES),
          setequal(unique(dc$period), PERIODS))
dc$area <- factor(dc$area, levels=CAUSES)
dc$pidx <- match(dc$period, PERIODS)
get_d <- function(a, p) dc$distance_km[dc$area==a & dc$period==p]
# spot values from the v2 frozen file (FREEZE_v2.md headline table)
stopifnot(abs(get_d("otitis_media","1995-1999") - 10180) <= 15,
          abs(get_d("otitis_media","2020-2024") - 2013) <= 15,
          abs(get_d("nasopharynx_cancer","2015-2019") - 978) <= 15,
          abs(get_d("nasopharynx_cancer","2020-2024") - 2467) <= 15)
# nasopharynx carries the one large last-step rebound (thyroid ticks up +82 km;
# every other cause falls in the last step)
last_step <- sapply(CAUSES, function(a)
  get_d(a,"2020-2024") - get_d(a,"2015-2019"))
stopifnot(last_step[["nasopharynx_cancer"]] > 1000,
          last_step[["nasopharynx_cancer"]] == max(last_step),
          all(last_step[setdiff(names(last_step),
                                c("nasopharynx_cancer","thyroid_cancer"))] < 0))
# distance fell first->last for all 7
stopifnot(all(sapply(CAUSES, function(a)
  get_d(a,"2020-2024") < get_d(a,"1995-1999"))))

## ---- panel c recompute (sanctioned): LMIC share, whole pool & excl. China ----
cc <- read.csv(file.path(ROOT,"data_l3/geo/country_counts.csv"),
               stringsAsFactors=FALSE)
ref <- read.csv(file.path(ROOT,"data_l3/geo/ref/country_reference.csv"),
                stringsAsFactors=FALSE)
stopifnot(all(cc$iso3 %in% ref$iso3))
cc$is_lmic <- ref$is_lmic[match(cc$iso3, ref$iso3)]
agg <- function(d) d %>% group_by(period) %>%
  summarise(n_total=sum(n), n_lmic=sum(n[is_lmic==1]), .groups="drop")
whole <- agg(cc)
# "Excluding China" series = decomposition of the whole-pool LMIC share:
# LMIC records excluding China, as a share of ALL parsed records (denominator
# stays the whole pool). This is the frozen headline definition: both endpoints
# reproduce 5.4% / 17.9% exactly (the alternative renormalised-pool definition
# gives 5.5% / 22.9% and fails the frozen assertions; not used).
excl_num <- cc[cc$iso3!="CHN",] %>% group_by(period) %>%
  summarise(n_lmic_excl=sum(n[is_lmic==1]), .groups="drop")
wi <- match(PERIODS, whole$period)
lmic <- data.frame(period=factor(PERIODS, levels=PERIODS),
                   pidx=seq_along(PERIODS),
                   lmic_share_all = whole$n_lmic[wi] / whole$n_total[wi] * 100,
                   lmic_share_excl_china = excl_num$n_lmic_excl[match(PERIODS, excl_num$period)] /
                                    whole$n_total[wi] * 100)
stopifnot(abs(lmic$lmic_share_all[1] - 7.9) <= 0.15,
          abs(lmic$lmic_share_all[6] - 39.8) <= 0.15,
          abs(lmic$lmic_share_excl_china[1] - 5.4) <= 0.15,
          abs(lmic$lmic_share_excl_china[6] - 17.9) <= 0.15)
write.csv(lmic[, c("period","lmic_share_all","lmic_share_excl_china")],
          file.path(ROOT,"data_l3/geo/centroid/lmic_series_recomputed.csv"),
          row.names=FALSE)

## ---- panel a: distance tile heatmap + first->last change strip ---------------
# Redesign (2026-11-12, chart-type quota \u00a71.3): panel a was a 7-line trajectory
# panel, which made line panels 2 of the figure's 3. It is now a tile heatmap
# (matrix data -> heatmap + one-side annotation strip, \u00a72) with a lollipop
# strip of the first->last % change sharing the rows. Rows are ordered by
# first-period distance, descending; the sequential single-hue scale runs
# light = short to dark = long, so every row lightening rightward IS the
# all-7-distances-fell result. Every cell prints its km value, so the fill
# scale carries no legend (V10/V12: one-side annotation strip, direct text,
# no duplicating legend); the figure's only legend remains the panel-b
# marker key (total 1 <= 2, V4). Row height: panel-a slot = 40 of 168 mm;
# measured on the rendered PNG, row pitch is ~4.2 mm and tile height
# (0.98 data units) is ~4.1 mm (>= 4 mm, V12).
ord_a <- CAUSES[order(sapply(CAUSES, function(a) get_d(a, "1995-1999")),
                      decreasing=TRUE)]
# rows strictly descending in first-period distance (v2: otitis 10,180 top,
# larynx 4,397 bottom), and the plotted heatmap matrix is exactly the file:
# every cause x period cell of hm reproduces dc$distance_km, nothing dropped
# or duplicated in reshaping.
stopifnot(all(diff(sapply(ord_a, function(a) get_d(a, "1995-1999"))) < 0))
hm <- dc
stopifnot(nrow(hm) == 42)
ypos_a <- setNames(seq_along(ord_a), ord_a)          # largest first-dist. on top
ypos_a <- setNames(8 - ypos_a, ord_a)                # (rank 1 -> y = 7)
hm$y <- ypos_a[as.character(hm$area)]
stopifnot(all(sapply(CAUSES, function(a)
  identical(sort(hm$distance_km[hm$area==a]),
            sort(dc$distance_km[dc$area==a])))))
hm$txt_col <- ifelse(hm$distance_km >= mean(range(dc$distance_km)),
                     "white", "#1F2A36")
hm$is_npc_last <- hm$area=="nasopharynx_cancer" & hm$pidx==6
chg <- data.frame(area=ord_a, y=unname(ypos_a[ord_a]))
chg$pct <- sapply(ord_a, function(a)
  (get_d(a, "2020-2024")/get_d(a, "1995-1999") - 1) * 100)
stopifnot(all(chg$pct < 0),
          abs(chg$pct[chg$area=="otitis_media"] - (-80.2)) <= 1)
chg$x0 <- 7.95                                        # strip zero line
chg$x1 <- 7.95 + chg$pct * (1.2/85)                   # -85% maps to x = 6.75
chg$lab <- sprintf("\u2212%d%%", round(abs(chg$pct)))
npc_y <- ypos_a[["nasopharynx_cancer"]]
pa <- ggplot(hm, aes(pidx, y)) +
  geom_tile(aes(fill=distance_km), width=0.94, height=0.98,
            colour="white", linewidth=0.7) +
  geom_text(data=hm[!hm$is_npc_last, ],
            aes(label=fmt_km(distance_km), colour=txt_col), size=2.5) +
  # NPC last cell: value nudged up, red triangle beside it, "rebound" tag below
  annotate("text", x=5.90, y=npc_y+0.16, label=fmt_km(get_d("nasopharynx_cancer","2020-2024")),
           colour="#1F2A36", size=2.5) +
  annotate("text", x=6.34, y=npc_y+0.16, label="\u25B2",
           colour=CCOL[["nasopharynx_cancer"]], size=2.1) +
  annotate("text", x=6, y=npc_y-0.29, label="rebound",
           colour=CCOL[["nasopharynx_cancer"]], size=2.0) +
  # first->last % change strip (one side only; stems/dots added below in CCOL)
  annotate("segment", x=6.58, xend=6.58, y=0.5, yend=7.5,
           colour="#CCCCCC", linewidth=0.3) +
  annotate("segment", x=7.95, xend=7.95, y=0.5, yend=7.5,
           colour="#999999", linewidth=0.35) +
  geom_text(data=chg, aes(x=8.06, y=y, label=lab), hjust=0, size=2.4,
            colour=COL$grey_txt) +
  annotate("text", x=1, y=7.82, label="Centroid distance (km)", hjust=0,
           size=2.2, colour=COL$grey_txt) +
  annotate("text", x=7.3, y=7.82, label="\u0394 first \u2192 last", hjust=0.5,
           size=2.2, colour=COL$grey_txt) +
  scale_fill_gradient(low="#E9F0F6", high="#274263", guide="none") +
  scale_colour_identity(guide="none") +
  scale_x_continuous(breaks=1:6, limits=c(0.45, 8.85), expand=c(0, 0),
                     labels=c("95\u201399","00\u201304","05\u201309",
                              "10\u201314","15\u201319","20\u201324")) +
  scale_y_continuous(breaks=1:7, limits=c(0.42, 7.98), expand=c(0, 0),
                     labels=LAB[rev(ord_a)]) +
  labs(x=NULL, y=NULL) +
  theme_fig(10) + theme(legend.position="none", panel.grid=element_blank(),
                        axis.text.y=element_text(colour=unname(CCOL[rev(ord_a)])))
for (i in seq_len(nrow(chg))) {          # strip stems + dots, one per row, CCOL
  pa <- pa + annotate("segment", x=chg$x0[i], xend=chg$x1[i],
                      y=chg$y[i], yend=chg$y[i],
                      colour=CCOL[[chg$area[i]]], linewidth=0.7) +
    annotate("point", x=chg$x1[i], y=chg$y[i], shape=21, size=1.6, stroke=0.4,
             colour=CCOL[[chg$area[i]]], fill=CCOL[[chg$area[i]]])
}

## ---- panel b: world basemap small multiples ----------------------------------
world <- map_data("world")
world <- world[world$region!="Antarctica" & world$lat > -60, ]
pts <- dc[dc$pidx %in% c(1,6), ] %>%
  pivot_longer(cols=c(burden_centroid_lon, research_centroid_lon),
               names_to="kind", values_to="lon") %>%
  mutate(lat=ifelse(kind=="burden_centroid_lon", burden_centroid_lat,
                    research_centroid_lat),
         kind=ifelse(kind=="burden_centroid_lon","Burden","Research"),
         shade=ifelse(pidx==1, 0.35, 1))
arr <- merge(pts[pts$pidx==1, c("area","kind","lon","lat")],
             pts[pts$pidx==6, c("area","kind","lon","lat")],
             by=c("area","kind"), suffixes=c("_f","_l"))
pb_map <- ggplot() +
  geom_polygon(data=world, aes(long, lat, group=group),
               fill="#D9D9D9", colour="white", linewidth=0.08) +
  geom_segment(data=arr, aes(x=lon_f, y=lat_f, xend=lon_l, yend=lat_l,
                             colour=area),
               linewidth=0.55, alpha=0.85,
               arrow=arrow(length=unit(1.4,"mm"), type="closed")) +
  geom_point(data=pts[pts$kind=="Burden",], aes(lon, lat, fill=area, alpha=shade),
             shape=21, size=1.9, stroke=0.5, colour="#333333") +
  geom_point(data=pts[pts$kind=="Research",], aes(lon, lat, colour=area, alpha=shade),
             shape=1, size=1.9, stroke=0.75) +
  scale_colour_manual(values=CCOL, guide="none") +
  scale_fill_manual(values=CCOL, guide="none") +
  scale_alpha_identity(guide="none") +
  facet_wrap(~area, ncol=3, labeller=as_labeller(LAB)) +
  coord_fixed(ratio=1.25, xlim=c(-168, 195), ylim=c(-58, 86)) +
  labs(x=NULL, y=NULL) +
  theme_fig(10) + theme(axis.text=element_blank(), axis.ticks=element_blank(),
                        axis.line.x=element_blank(), axis.line.y=element_blank(),
                        panel.grid.major.y=element_blank(),
                        strip.text=element_text(size=7.5),
                        legend.position="none")
# marker key (the figure's single legend): filled = burden, open = research;
# pale = 1995-99, strong = 2020-24
key_df <- data.frame(x=1, y=c(4,3,2,1),
                     kind=c("Burden","Burden","Research","Research"),
                     shade=c(1, 0.35, 1, 0.35),
                     lab=c("Burden 2020\u201324","Burden 1995\u201399",
                           "Research 2020\u201324","Research 1995\u201399"))
key_df$tx <- key_df$x + 0.16
pkey <- ggplot(key_df, aes(x, y)) +
  geom_point(aes(shape=kind, alpha=shade), size=2.8, stroke=0.85,
             colour=COL$grey_txt, fill=COL$grey_txt) +
  geom_text(aes(tx, y, label=lab), hjust=0, size=2.3,
            colour=COL$grey_txt) +
  scale_shape_manual(values=c(Burden=21, Research=1), guide="none") +
  scale_alpha_identity(guide="none") +
  xlim(0.9, 2.6) + ylim(0.55, 4.45) + theme_void() +
  theme(text=element_text(family="Arial"))
pb <- wrap_elements(full=(pb_map | pkey) + plot_layout(widths=c(5.2, 1)))

## ---- panel c: LMIC share ------------------------------------------------------
cl <- lmic %>% pivot_longer(cols=c(lmic_share_all, lmic_share_excl_china),
                            names_to="series", values_to="share") %>%
  mutate(series=ifelse(series=="lmic_share_all","All areas",
                       "Excluding China"))
cend <- cl[cl$pidx==6, ]
first_share <- c("All areas"=lmic$lmic_share_all[1],
                 "Excluding China"=lmic$lmic_share_excl_china[1])
cend$text <- sprintf("%s  %.1f\u2192%.1f%%", cend$series,
                     first_share[cend$series], cend$share)
pc <- ggplot(cl, aes(pidx, share, colour=series, group=series)) +
  geom_line(linewidth=0.9) + geom_point(size=1.5) +
  geom_text(data=cend, aes(x=6.18, y=share, label=text), hjust=0, size=2.35,
            colour=COL$grey_txt) +
  scale_colour_manual(values=c("All areas"=COL$disease2,
                               "Excluding China"=COL$accent)) +
  scale_x_continuous(breaks=1:6, limits=c(1, 9.4),
                     labels=c("95\u201399","00\u201304","05\u201309",
                              "10\u201314","15\u201319","20\u201324")) +
  labs(x=NULL, y="LMIC first-author share (%)") +
  theme_fig(10) + theme(legend.position="none")

fig5 <- pa / pb / pc + plot_layout(heights=c(40, 92, 36)) +
  plot_annotation(tag_levels="a") &
  theme(plot.tag=element_text(size=12.5, face="bold", family="Arial"))
save_fig(fig5, file.path(ROOT,"figures/fig5"), width_mm=180, height_mm=168)
cat("fig5 done\n")

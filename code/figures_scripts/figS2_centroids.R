#!/usr/bin/env Rscript
# Fig S2 (supplementary) — Research centroids, all 14 areas.
# Conclusions carried: (a) first- and last-period research-centroid
#   coordinates and total drift for every area (burden tier in Fig 4 covers
#   burden-vs-research distance; here the research centroid itself, all 14);
#   (b) on world maps, the attention-tier research centroids moved between
#   1995-99 (open) and 2020-24 (filled).
# Source (frozen v2): data_l3/geo/centroid/research_centroids_all14.csv
#   (84 rows; weighted mean centre of parsed first-author records over
#   country centres — weighted mean latitude, circular mean longitude;
#   see data_l3/geo/centroid/FREEZE_v2.md). Drift is computed in this
#   script from the file's lat/lon (haversine, R = 6371.0088 km).
# v2 estimator redraw 2026-11-12: the previous render used the archived
#   chordal (unit-vector) centroids; every coordinate and drift below now
#   comes from the v2 arithmetic mean-centre file.
# IRON RULE: every number from the frozen file; stopifnot throughout.
source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages({ library(patchwork); library(colorspace);
                                 library(maps) })

ROOT <- "~/workspace/ent-attention-burden"
PERIODS <- c("1995-1999","2000-2004","2005-2009","2010-2014","2015-2019","2020-2024")
BURDEN <- c("otitis_media","hearing_loss","larynx_cancer","oral_cancer",
            "nasopharynx_cancer","other_pharynx_cancer","thyroid_cancer")
ATT <- c("osa","crs_polyps","cochlear_implant","allergic_rhinitis",
         "tinnitus","vertigo","cholesteatoma")
LAB <- c(hearing_loss="Hearing loss", otitis_media="Otitis media",
         nasopharynx_cancer="Nasopharyngeal cancer",
         thyroid_cancer="Thyroid cancer", oral_cancer="Oral cancer",
         other_pharynx_cancer="Other pharyngeal cancer",
         larynx_cancer="Laryngeal cancer",
         osa="Obstructive sleep apnoea", crs_polyps="CRS / polyps",
         allergic_rhinitis="Allergic rhinitis",
         cochlear_implant="Cochlear implant", tinnitus="Tinnitus",
         vertigo="Vertigo", cholesteatoma="Cholesteatoma")
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

## ---- data + assertions -----------------------------------------------------------
rc <- read.csv(file.path(ROOT,"data_l3/geo/centroid/research_centroids_all14.csv"),
               stringsAsFactors=FALSE)
stopifnot(nrow(rc)==84, setequal(unique(rc$area), c(BURDEN, ATT)),
          setequal(unique(rc$period), PERIODS), all(table(rc$area)==6),
          all(rc$centroid_coverage_of_parsed > 0.999),
          all(abs(rc$research_centroid_lat) <= 50))   # v2 guard (FREEZE_v2)
hav <- function(lat1, lon1, lat2, lon2) {
  R <- 6371.0088; rad <- pi/180
  dlat <- (lat2-lat1)*rad; dlon <- (lon2-lon1)*rad
  a <- sin(dlat/2)^2 + cos(lat1*rad)*cos(lat2*rad)*sin(dlon/2)^2
  2 * R * asin(pmin(1, sqrt(a)))
}
w <- data.frame(area=c(BURDEN, ATT), stringsAsFactors=FALSE)
for (a in w$area) {
  f <- rc[rc$area==a & rc$period=="1995-1999", ]
  l <- rc[rc$area==a & rc$period=="2020-2024", ]
  stopifnot(nrow(f)==1, nrow(l)==1)
  w$lat1[w$area==a] <- f$research_centroid_lat; w$lon1[w$area==a] <- f$research_centroid_lon
  w$lat2[w$area==a] <- l$research_centroid_lat; w$lon2[w$area==a] <- l$research_centroid_lon
}
w$drift <- hav(w$lat1, w$lon1, w$lat2, w$lon2)
stopifnot(all(w$drift > 0 & w$drift < 20000))
# v2 spot values from the FREEZE v2 run (tolerance 25 km)
stopifnot(abs(w$drift[w$area=="allergic_rhinitis"]  - 8084) < 25,
          abs(w$drift[w$area=="cochlear_implant"]   - 2839) < 25,
          abs(w$drift[w$area=="nasopharynx_cancer"] - 1930) < 25,
          w$area[which.min(w$drift)] == "nasopharynx_cancer",
          w$area[which.max(w$drift)] == "allergic_rhinitis")
cat("research-centroid drift 1995-99 -> 2020-24 (km):\n")
for (i in order(-w$drift))
  cat(sprintf("  %-22s %6.0f\n", w$area[i], w$drift[i]))

## ---- panel a: aligned numeric grid (V7) --------------------------------------------
fmt_lat <- function(v) sprintf("%.1f\u00b0%s", abs(v), ifelse(v>=0, "N", "S"))
fmt_lon <- function(v) sprintf("%.1f\u00b0%s", abs(v), ifelse(v>=0, "E", "W"))
w$y <- c(14:8, 7:1)                       # burden rows 14-8, attention rows 7-1
w$name <- LAB[w$area]
w$col <- AREA_COL[w$area]
CX <- c(lat1=42, lon1=57, lat2=72, lon2=87, drift=100)
hdr <- data.frame(x=c(0, CX), label=c("Area","1995\u201399 lat","1995\u201399 lon",
                                      "2020\u201324 lat","2020\u201324 lon",
                                      "Drift (km)"),
                  hj=c(0,1,1,1,1,1), stringsAsFactors=FALSE)
num_a <- rbind(
  data.frame(x=CX["lat1"], y=w$y, txt=fmt_lat(w$lat1)),
  data.frame(x=CX["lon1"], y=w$y, txt=fmt_lon(w$lon1)),
  data.frame(x=CX["lat2"], y=w$y, txt=fmt_lat(w$lat2)),
  data.frame(x=CX["lon2"], y=w$y, txt=fmt_lon(w$lon2)),
  data.frame(x=CX["drift"], y=w$y,
             txt=formatC(round(w$drift), format="d", big.mark=",")))
pa <- ggplot() +
  annotate("segment", x=0, xend=101, y=15.05, yend=15.05,
           colour="#999999", linewidth=0.5) +
  annotate("segment", x=0, xend=101, y=7.5, yend=7.5,
           colour="#DDDDDD", linewidth=0.4) +
  geom_text(data=hdr, aes(x=x, y=15.55, label=label, hjust=hj),
            size=SZ_LAB/2.85, fontface="bold", colour=COL$grey_txt) +
  geom_text(data=w, aes(x=0, y=y, label=name, colour=col),
            hjust=0, size=SZ_LAB/2.85) +
  scale_colour_identity() +
  geom_text(data=num_a, aes(x=x, y=y, label=txt), hjust=1,
            size=SZ_LAB/2.85, colour=COL$grey_txt) +
  scale_x_continuous(limits=c(0, 101)) +
  scale_y_continuous(limits=c(0.4, 16.1)) +
  labs(x=NULL, y=NULL) +
  coord_cartesian(clip="off") +
  theme_fig(9) + theme(axis.text=element_blank(), axis.ticks=element_blank(),
                       axis.line.x=element_blank(), axis.line.y=element_blank(),
                       panel.grid.major.y=element_blank(),
                       legend.position="none",
                       plot.margin=margin(4, 4, 2, 4))

## ---- panel b: attention-tier centroid maps -------------------------------------------
world <- map_data("world")
world <- world[world$region!="Antarctica", ]
att_rc <- rc[rc$area %in% ATT, ]
seg <- data.frame(area=ATT,
                  lon1=w$lon1[match(ATT, w$area)], lat1=w$lat1[match(ATT, w$area)],
                  lon2=w$lon2[match(ATT, w$area)], lat2=w$lat2[match(ATT, w$area)],
                  stringsAsFactors=FALSE)
seg$area <- factor(seg$area, levels=ATT)
pt_first <- data.frame(area=seg$area, lon=seg$lon1, lat=seg$lat1)
pt_last  <- data.frame(area=seg$area, lon=seg$lon2, lat=seg$lat2)
pb <- ggplot() +
  geom_polygon(data=world, aes(long, lat, group=group),
               fill="#E9E9E9", colour="white", linewidth=0.12) +
  geom_segment(data=seg, aes(x=lon1, y=lat1, xend=lon2, yend=lat2, colour=area),
               arrow=arrow(length=unit(1.7, "mm"), type="closed"),
               linewidth=0.75) +
  geom_point(data=pt_first, aes(lon, lat, colour=area),
             shape=21, fill="white", size=2.1, stroke=0.8) +
  geom_point(data=pt_last, aes(lon, lat, fill=area),
             shape=21, colour="white", size=2.2, stroke=0.5) +
  scale_colour_manual(values=AREA_COL, guide="none") +
  scale_fill_manual(values=AREA_COL, guide="none") +
  facet_wrap(~area, ncol=4, labeller=labeller(area=LAB)) +
  coord_quickmap(xlim=c(-180, 180), ylim=c(-58, 84)) +
  labs(x=NULL, y=NULL) +
  theme_void(base_family="Arial") +
  theme(strip.text=element_text(size=8, face="bold", colour=COL$grey_txt),
        legend.position="none",
        plot.margin=margin(4, 4, 2, 4))

figS2 <- pa / pb + plot_layout(heights=c(78, 52)) +
  plot_annotation(tag_levels="a",
                  theme=theme(plot.tag=element_text(size=12, face="bold",
                                                    family="Arial")))
save_fig(figS2, file.path(ROOT,"figures/figS2"), width_mm=180, height_mm=130)
cat("figS2 done\n")

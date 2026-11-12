#!/usr/bin/env Rscript
# Fig 5 — Decoupling typology (descriptive classification; thresholds operationalised
# at the analysis stage 2026-11-12, NOT preregistered inference).
# Conclusions carried: (a) anchor matrix — signal directions + magnitudes per cause,
#   assigned type at main thresholds; 3 of 7 causes honestly unclassified;
#   hearing loss is "constant" in dynamics only, at ABR 0.36 (deep under-attention).
#   (b) assignments under low/main/high thresholds: nasopharynx + oral are the only
#   fully robust types. (c) attention tier carries share-dynamics labels only;
#   CRS is asterisked (modern-terminology sensitivity query reverses its direction).
# Sources (frozen): data_l4/signals.csv, data_l4/typology.csv.
# IRON RULE: every number from the frozen files; stopifnot throughout.
source("~/workspace/custom-skills/figure_style_v3/figstyle_v3.R")
suppressPackageStartupMessages({ library(patchwork); library(tidyr) })

ROOT <- "~/workspace/ent-attention-burden"
LAB <- c(otitis_media="Otitis media", hearing_loss="Hearing loss",
         larynx_cancer="Larynx cancer", oral_cancer="Oral cancer",
         nasopharynx_cancer="Nasopharynx cancer",
         other_pharynx_cancer="Other pharynx cancer",
         thyroid_cancer="Thyroid cancer",
         allergic_rhinitis="Allergic rhinitis", cholesteatoma="Cholesteatoma",
         cochlear_implant="Cochlear implant", crs_polyps="CRS / polyps",
         osa="OSA", tinnitus="Tinnitus", vertigo="Vertigo")
ORDER <- c("otitis_media","nasopharynx_cancer","oral_cancer","hearing_loss",
           "larynx_cancer","other_pharynx_cancer","thyroid_cancer")
TYPE_LAB <- c(resolution_dilution="Resolution-dilution",
              technology_ignited="Technology-ignited",
              constant="Constant", burden_tracking="Burden-tracking",
              unclassified="Unclassified")
TYPE_SHORT <- c(resolution_dilution="Dilution", technology_ignited="Ignited",
                constant="Constant", burden_tracking="Tracking",
                unclassified="Unclassified")
TYPE_COL <- c(resolution_dilution="#4DBBD5", technology_ignited="#E64B35",
              constant="#8491B4", burden_tracking="#7E6148",
              unclassified="#D9D9D9")
DIR_COL <- c(up="#E64B35", down="#4DBBD5", stable="#8491B4")

sig <- read.csv(file.path(ROOT,"data_l4/signals.csv"), stringsAsFactors=FALSE)
typ <- read.csv(file.path(ROOT,"data_l4/typology.csv"), stringsAsFactors=FALSE)
stopifnot(nrow(sig)==14, nrow(typ)==14)
bur <- sig[sig$tier=="burden", ]; att <- sig[sig$tier=="attention", ]
stopifnot(nrow(bur)==7, nrow(att)==7, setequal(bur$area, ORDER))
tmap <- typ$type_main[match(ORDER, typ$area)]
names(tmap) <- ORDER
expected <- c(otitis_media="resolution_dilution",
              nasopharynx_cancer="technology_ignited",
              oral_cancer="technology_ignited", hearing_loss="constant",
              larynx_cancer="unclassified",
              other_pharynx_cancer="unclassified",
              thyroid_cancer="unclassified")
stopifnot(identical(unname(tmap), unname(expected[ORDER])))
# nasopharynx + oral identical across all three threshold sets
for (a in c("nasopharynx_cancer","oral_cancer")) {
  r <- typ[typ$area==a, ]
  stopifnot(r$type_low==r$type_main, r$type_high==r$type_main,
            r$robust_across_thresholds==1)
}
hl <- bur[bur$area=="hearing_loss", ]
stopifnot(abs(2^hl$log2abr_last - 0.36) < 0.005)  # ABR 0.36 must be visible

yfac <- function(d) { d$area <- factor(d$area, levels=rev(ORDER)); d }

## ---- panel a (anchor): signal matrix + type labels ---------------------------
cells <- do.call(rbind, lapply(ORDER, function(a) {
  r <- bur[bur$area==a, ]
  data.frame(area=a,
             metric=c("S","B","A","L"),
             text=c(sprintf("%+.1f%%", r$S_rel_pct),
                    sprintf("%+.1f%%", r$B_rel_pct),
                    sprintf("%+.2f", r$A_delta),
                    if (a=="hearing_loss") sprintf("%+.2f\nABR 0.36", r$log2abr_last)
                    else sprintf("%+.2f", r$log2abr_last)),
             dir=c(r$S_dir_main, r$B_dir_main, r$A_dir_main,
                   ifelse(r$log2abr_last < 0, "down", "up")),
             stringsAsFactors=FALSE)
}))
cells <- yfac(cells)
cells$metric <- factor(cells$metric, levels=c("S","B","A","L"))
tlab <- data.frame(area=factor(ORDER, levels=rev(ORDER)),
                   text=unname(TYPE_LAB[tmap]), type=unname(tmap))
pa <- ggplot(cells, aes(metric, area)) +
  geom_tile(aes(fill=dir), alpha=0.5, colour="white", linewidth=0.8) +
  geom_tile(data=cells[cells$area=="hearing_loss" & cells$metric=="L", ],
            fill=NA, colour="#333333", linewidth=0.7) +
  geom_text(aes(label=text), size=2.5, colour="#1A1A1A") +
  geom_text(data=tlab, aes(x=4.68, y=area, label=text, colour=type),
            hjust=0, size=2.55, fontface="bold") +
  scale_fill_manual(values=DIR_COL, guide="none") +
  scale_colour_manual(values=c(resolution_dilution="#2F7E96",
                               technology_ignited="#C93A26",
                               constant="#6E7CA6", burden_tracking="#7E6148",
                               unclassified="#8A8A8A"), guide="none") +
  scale_x_discrete(position="top",
                   labels=c(S="S (share)", B="B (DALY share)",
                            A="\u0394 log2 ABR", L="log2 ABR, last")) +
  scale_y_discrete(labels=LAB) +
  coord_cartesian(xlim=c(0.5, 6.1), clip="off") +
  labs(x=NULL, y=NULL) +
  theme_fig(10) + theme(axis.line.x=element_blank(), axis.line.y=element_blank(),
                        axis.ticks=element_blank(),
                        panel.grid.major.y=element_blank(),
                        axis.text.x.top=element_text(size=8, face="bold"),
                        axis.text.y=element_text(size=8),
                        legend.position="none")

## ---- panel b: threshold sensitivity ------------------------------------------
blong <- typ[typ$tier=="burden", ] %>%
  pivot_longer(cols=c(type_low, type_main, type_high),
               names_to="set", values_to="type") %>%
  mutate(set=factor(set, levels=c("type_low","type_main","type_high"),
                    labels=c("Low","Main","High")),
         short=unname(TYPE_SHORT[type]))
blong <- yfac(blong)
pb <- ggplot(blong, aes(set, area)) +
  geom_tile(aes(fill=type), alpha=0.85, colour="white", linewidth=0.8) +
  geom_text(aes(label=short), size=2.35,
            colour=ifelse(blong$type=="unclassified", "#555555", "white"),
            fontface="bold") +
  scale_fill_manual(values=TYPE_COL, guide="none") +
  scale_x_discrete(position="top") +
  scale_y_discrete(labels=LAB) +
  labs(x=NULL, y=NULL) +
  theme_fig(10) + theme(axis.line.x=element_blank(), axis.line.y=element_blank(),
                        axis.ticks=element_blank(),
                        panel.grid.major.y=element_blank(),
                        axis.text.x.top=element_text(size=8, face="bold"),
                        axis.text.y=element_text(size=8),
                        legend.position="none")

## ---- panel c: attention-tier strip --------------------------------------------
AORD <- c("cholesteatoma","allergic_rhinitis","crs_polyps","osa",
          "cochlear_implant","tinnitus","vertigo")
DYN <- c(cholesteatoma="Down", allergic_rhinitis="Down", crs_polyps="Down*",
         osa="Up", cochlear_implant="\u2248stable\nmild \u2193 (backup)",
         tinnitus="\u2248flat\nmild \u2193 (backup)", vertigo="Stable")
DFILL <- c(cholesteatoma="down", allergic_rhinitis="down", crs_polyps="down",
           osa="up", cochlear_implant="stable", tinnitus="stable",
           vertigo="stable")
att_d <- data.frame(area=factor(AORD, levels=AORD),
                    text=unname(DYN[AORD]), fill=unname(DFILL[AORD]), y=1)
pc <- ggplot(att_d, aes(area, y)) +
  geom_tile(aes(fill=fill), alpha=0.65, colour="white", linewidth=0.8,
            height=0.92) +
  geom_text(aes(label=text), size=2.3, colour="#1A1A1A") +
  scale_fill_manual(values=DIR_COL, guide="none") +
  scale_x_discrete(position="top",
                   labels=c(cholesteatoma="Cholesteatoma",
                            allergic_rhinitis="Allergic\nrhinitis",
                            crs_polyps="CRS / polyps", osa="OSA",
                            cochlear_implant="Cochlear\nimplant",
                            tinnitus="Tinnitus", vertigo="Vertigo")) +
  scale_y_continuous(breaks=NULL) +
  labs(x=NULL, y=NULL) +
  theme_fig(10) + theme(axis.line.x=element_blank(), axis.line.y=element_blank(),
                        axis.ticks=element_blank(),
                        panel.grid.major.y=element_blank(),
                        axis.text.x.top=element_text(size=7.5),
                        legend.position="none")

fig6 <- pa / pb / pc + plot_layout(heights=c(84, 40, 26)) +
  plot_annotation(tag_levels="a") &
  theme(plot.tag=element_text(size=12.5, face="bold", family="Arial"))
save_fig(fig6, file.path(ROOT,"figures/fig6"), width_mm=180, height_mm=160)
cat("fig6 done\n")

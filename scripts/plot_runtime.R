#!/usr/bin/env Rscript

library(data.table)
library(ggplot2)

options(width = 600)

grp4_colors <- c("#E18727FF", "#0072B5FF", "#925E9FFF", "#AD002AFF")

plot_theme <- theme(
  axis.text.x = element_blank(),
  axis.text.y = element_text(size = 14, color = "black"),
  axis.title.x = element_text(size = 14, color = "black"),
  axis.title.y = element_text(size = 14, color = "black"),
  panel.grid.major = element_blank(),
  panel.grid.minor = element_blank(),
  panel.background = element_blank(),
  axis.line = element_line(colour = "black"),
  legend.position = c(0.1, 0.95),
  legend.justification = c("right", "top"),
  legend.key = element_blank(),
  legend.text = element_text(size = 12)
)

args <- commandArgs(trailingOnly = TRUE)

data <- args[1]
out <- args[2]

dt <- fread(data)
# order by og runtime
og_time_dt <- dt[mode == "OG"]
sample_order <- og_time_dt[order(TotTime)]$SampleID

dt[, mode := factor(mode, levels = c("faster", "fast", "OG"))]
dt[, SampleID := factor(SampleID, levels = sample_order)]
m <- ggplot(dt, aes(x = SampleID, y = TotTime, fill = mode)) +
  geom_bar(stat = "identity", position = "dodge") +
  scale_fill_manual(values = grp4_colors[1:3]) +
  ylab("Realignment Runtime") +
  plot_theme
ggsave(out, m, width = 18, height = 6)

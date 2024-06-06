#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(splitstackshape)
})

options(width = 600)

evaluate <- function(row) {
  p1 <- row["p1"]
  p2 <- row["p2"]
  t <- c(row["e1"], row["e2"])
  n <- 0
  m1 <- match(p1, t)
  if (!is.na(m1)) {
    t <- t[-m1]
    n <- n + 1
  }
  m2 <- match(p2, t)
  if (!is.na(m2)) {
    n <- n + 1
  }
  n
}

args <- commandArgs(trailingOnly = TRUE)

res <- args[1]
truth <- args[2]
out <- args[3]

truth_dt <- fread(truth, keepLeadingZeros = TRUE)
names(truth_dt) <- gsub(" ", "_", names(truth_dt))
truth_long_dt <- melt(
  truth_dt,
  id.vars = c("SampleID", "Region", "Population"),
  variable.name = "gene",
  value.name = "D4_truth"
)
truth_long_dt[, gene := tolower(gsub("_(1|2)$", "", gene))]
truth_long_dt[, gene := gsub("-", "_", gene)]
truth_long_dt[, D4_truth := sort(D4_truth), by = list(SampleID, gene)]
truth_long_dt[, D4_truth := gsub("\\*$", "", D4_truth)]
names(truth_long_dt)[1] <- "sample"
truth_long_dt <- truth_long_dt[order(sample, gene)]

res_dt <- fread(res, keepLeadingZeros = TRUE)
res_dt <- res_dt[order(sample, gene)]

genes <- intersect(truth_long_dt$gene, res_dt$gene)

res_dt <- res_dt[gene %in% genes]
truth_long_dt <- truth_long_dt[gene %in% genes]
truth_long_dt[, "tmp" := paste(
  D4_truth,
  collapse = ","
), by = list(sample, gene)]
truth_long_dt <- unique(truth_long_dt, by = c("sample", "tmp"))
truth_long_dt[, c("e1", "e2") := tstrsplit(tmp, ",", fixed = TRUE)]
truth_long_dt[, ":="(tmp = NULL, D4_truth = NULL)]
res_dt[, "tmp" := paste(D4, collapse = ","), by = list(sample, gene)]
res_dt <- unique(res_dt, by = c("sample", "tmp"))
res_dt[, c("p1", "p2") := tstrsplit(tmp, ",", fixed = TRUE)]
res_dt[, ":="(tmp = NULL, D4 = NULL, D6 = NULL)]

eval_dt <- merge(res_dt, truth_long_dt, by = c("sample", "gene"), all.x = TRUE)
eval_dt[, n_match := apply(
  .SD, 1, evaluate
), .SDcols = c("p1", "p2", "e1", "e2")]
print(eval_dt[n_match < 2])
n_expect_to_match <- nrow(eval_dt) * 2
n_match <- sum(eval_dt$n_match)
print(n_expect_to_match)
print(n_match)
print(n_match / n_expect_to_match)
fwrite(eval_dt, out, sep = "\t", row.names = FALSE, quote = FALSE)

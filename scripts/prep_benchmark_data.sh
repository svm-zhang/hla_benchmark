#!/usr/bin/env bash

function info() {
  echo "[$1] INFO: $2"
}

function download_bam() {
  local url=$1
  local outdir=$2

  cmd="aws s3 cp --no-sign-request ${url} ${outdir} --recursive --exclude \"*\" --include \"*mapped*.bam\" "
  if ! eval "${cmd}"; then
    echo "[ERROR] Download BAM using aws s3 cp failed"
    exit 1
  fi

}

function run_bam2fq() {
  local bam=$1
  local r1=$2
  local r2=$3

  if [ ! -f "${bam}" ]; then
    echo "[ERROR] Cannot find the given ${bam} to extract fastq"
    exit 1
  fi

  prefix="${bam}.tmp."
  cmd="samtools sort -T${prefix} -@${thread} -m 2G -n ${bam} | samtools bam2fq -1 ${r1} -2 ${r2} -0 /dev/null -s /dev/null -"
  if ! eval "${cmd}"; then
    echo "[ERROR] Extract FQ from ${bam} failed"
    exit 1
  fi

}

sample_id=$1
wkdir=$2
thread=4

sample_dir="${wkdir}/${sample_id}"
bam_dir="${sample_dir}/bam"
fq_dir="${sample_dir}/fq"
log_dir="${sample_dir}/log"

if [ ! -d "${bam_dir}" ]; then
  mkdir -p "${bam_dir}"
fi

if [ ! -d "${fq_dir}" ]; then
  mkdir -p "${fq_dir}"
fi

if [ ! -d "${log_dir}" ]; then
  mkdir -p "${log_dir}"
fi

info "main" "Download mapped BAM for ${sample_id}"
s3_url="s3://1000genomes/phase3/data/${sample_id}/exome_alignment/"
download_done="${log_dir}/${sample_id}.download.done"
if [ ! -f "${download_done}" ]; then
  download_bam "${s3_url}" "${bam_dir}"
  touch "${download_done}"
else
  info "main" "Previous download was done. Skip"
fi

mapped_bam=$(find "${bam_dir}" -name "${sample_id}.mapped*.bam")
unmapped_bam=$(find "${bam_dir}" -name "${sample_id}.unmapped*.bam")

info "main" "Extract Fastq from ${mapped_bam}"
extract_mapped_done="${log_dir}/${sample_id}.extract.mapped.done"
m_r1="${fq_dir}/${sample_id}.mapped.R1.fastq.gz"
m_r2="${fq_dir}/${sample_id}.mapped.R2.fastq.gz"
if [ ! -f "${extract_mapped_done}" ]; then
  run_bam2fq "${mapped_bam}" "${m_r1}" "${m_r2}"
  touch "${extract_mapped_done}"
else
  info "main" "Previous extraction was done. Skip"
fi

info "main" "Extract Fastq from ${unmapped_bam}"
extract_unmapped_done="${log_dir}/${sample_id}.extract.unmapped.done"
un_r1="${fq_dir}/${sample_id}.unmapped.R1.fastq.gz"
un_r2="${fq_dir}/${sample_id}.unmapped.R2.fastq.gz"
if [ ! -f "${extract_unmapped_done}" ]; then
  run_bam2fq "${unmapped_bam}" "${un_r1}" "${un_r2}"
  touch "${extract_unmapped_done}"
else
  info "main" "Previous extraction was done. Skip"
fi

final_r1="${fq_dir}/${sample_id}.R1.fastq.gz"
final_r2="${fq_dir}/${sample_id}.R2.fastq.gz"

if [ ! -f "${final_r1}" ] || [ ! -f "${final_r2}" ]; then
  cat "${m_r1}" "${un_r1}" > "${final_r1}"
  cat "${m_r2}" "${un_r2}" > "${final_r2}"
  rm "${m_r1}" "${m_r2}" "${un_r1}" "${un_r2}"
fi

all_done="${log_dir}/${sample_id}.prep.done"
touch "${all_done}"

info "main" "Prep done"

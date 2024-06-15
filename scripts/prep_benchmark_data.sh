#!/usr/bin/env bash

function info() {
  echo "[$1] INFO: $2"
}

function error() {
  echo "[$1:$2] ERROR: $3" 1>&2
}

function die () {
	rc=$?
	# when there is argument passing in "$#"
	# error the message
	(( $# )) && error "$1" "$2" "$3"
	exit "$(( rc == 0 ? 1 : rc ))"
}

function download_bam() {
  local url=$1
  local outdir=$2

  aws s3 cp --no-sign-request "$url" "$outdir" --recursive \
    --exclude "*" --include "*mapped*.bam" \
    || die "${FUNCNAME[0]}" "$LINENO" "Failed to run aws s3 cp to download"

}

function run_bam2fq() {
  local bam=$1
  local r1=$2
  local r2=$3

  if [ ! -f "${bam}" ]; then
    error "${FUNCNAME[0]}" "${LINENO}" "Cannot find the given ${bam} to extract fastq"
    exit 1
  fi

  prefix="${bam}.tmp."
  samtools sort -T"$prefix" -@"$thread" -n "$bam" 2>/dev/null\
    | samtools bam2fq -1 "$r1" -2 "$r2" -0 /dev/null -s /dev/null - \
    || die "${FUNCNAME[0]}" "$LINENO" "Failed to get Fastq from BAM"

}

sample_id=$1
wkdir=$2
thread=$3

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
  nbam=$( find "${bam_dir}" -name "*.bam" | wc -l )
  if [ "${nbam}" == 0 ]; then
    info "main" "No BAM files were downloaded"
    info "main" "Clean folder. Exit"
    rm -r "${sample_dir}"
    exit 0
  fi
  touch "${download_done}"
else
  info "main" "Previous download was done. Skip"
fi

mapped_bam=$(find "${bam_dir}" -name "${sample_id}.mapped*.bam")
unmapped_bam=$(find "${bam_dir}" -name "${sample_id}.unmapped*.bam")

if [ ! -f "$mapped_bam" ] && [ ! -f "$unmapped_bam" ]; then
  info "$0" "$LINENO" "Looks like no BAM files downloaded"
  info "$0" "$LINENO" "Nothing to do next. Exit now"
  exit 0
fi

sort_bam="${bam_dir}/${sample_id}.merged.so.bam"
if [ ! -f "$sort_bam" ]; then
  info "main" "Merge and sort BAMs for ${sample_id}"
  samtools cat "$mapped_bam" "$unmapped_bam" \
    | samtools sort -T"${sample_id}_tmp" -@"$thread" -o "$sort_bam" - \
    || die "$0" "$LINENO" "Failed to cat and sort BAM files"

  samtools index "$sort_bam" \
    || die "$0" "$LINENO" "Failed to index sorted BAM file"
fi

final_r1="${fq_dir}/${sample_id}.R1.fastq.gz"
final_r2="${fq_dir}/${sample_id}.R2.fastq.gz"
if [ ! -f "${final_r1}" ] || [ ! -f "${final_r2}" ]; then
  info "main" "Extract Fastq from ${sort_bam}"
  run_bam2fq "${sort_bam}" "${final_r1}" "${final_r2}"
else
  info "main" "Previous extraction was done. Skip"
fi

all_done="${log_dir}/${sample_id}.prep.done"
touch "${all_done}"

info "main" "Prep done"

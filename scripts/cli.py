from __future__ import annotations

import argparse

from pathio import parse_path


def parse_cmd() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--sample",
        metavar="STR",
        type=str,
        required=True,
        help="specify sample ID",
    )
    parent_parser.add_argument(
        "--hlaref",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA reference in Fasta",
    )
    parent_parser.add_argument(
        "--freq",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA population frequency file",
    )
    parent_parser.add_argument(
        "--wkdir",
        metavar="DIR",
        type=parse_path,
        required=True,
        help="specify path to output directory",
    )
    parent_parser.add_argument(
        "--scheduler",
        metavar="STR",
        type=str,
        default="slurm",
        choices=["slurm", "sge", "bash"],
        help="specify name of job scheduler (slurm, sge, bash) [slurm]",
    )
    parent_parser.add_argument(
        "--realign_only",
        action="store_true",
        help="specify to only run realigner",
    )
    parent_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="specify whether or not to overwrite job file",
    )
    parent_parser.add_argument(
        "--nproc",
        metavar="INT",
        type=int,
        default=8,
        help="specify the number of process requested [8]",
    )
    parent_parser.add_argument(
        "--ram",
        metavar="INT",
        type=int,
        default=4,
        help="specify the maximum RAM requested in GB [4]",
    )

    commands = parser.add_subparsers(title="Commands", dest="command")
    hlareforged = commands.add_parser("hlareforged", parents=[parent_parser])
    hlareforged.add_argument(
        "--r1",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify R1 reads in FASTQ",
    )
    hlareforged.add_argument(
        "--r2",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify R2 reads in FASTQ",
    )
    hlareforged.add_argument(
        "--nproc_per_job",
        metavar="INT",
        type=int,
        default=2,
        help="specify the number of process per razers3 job [2]",
    )

    polysolver = commands.add_parser("polysolver", parents=[parent_parser])
    polysolver.add_argument(
        "--bam",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify BAM file",
    )
    polysolver.add_argument(
        "--bed",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA bed file",
    )
    polysolver.add_argument(
        "--tag",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA kmer tag file",
    )
    polysolver.add_argument(
        "--fish_mode",
        metavar="STR",
        type=str,
        default="faster",
        choices=["faster", "fast"],
        help="specify fishing mode [faster]",
    )

    return parser

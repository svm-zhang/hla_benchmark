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
        choices=["slurm", "bash"],
        help="specify name of job scheduler (slurm, bash) [slurm]",
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
    polysolvermod = commands.add_parser("polysolvermod", parents=[parent_parser])
    polysolvermod.add_argument(
        "--bam",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify BAM file",
    )
    polysolvermod.add_argument(
        "--bed",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA bed file",
    )
    polysolvermod.add_argument(
        "--tag",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA kmer tag file",
    )
    polysolvermod.add_argument(
        "--fish_mode",
        metavar="STR",
        type=str,
        default="faster",
        choices=["faster", "fast"],
        help="specify fishing mode [faster]",
    )

    return parser

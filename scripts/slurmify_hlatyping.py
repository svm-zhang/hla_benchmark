from __future__ import annotations

import argparse

from command import Command

from cli import parse_cmd
from job import jobfy


@jobfy
def run_hlareforged(args: argparse.Namespace):

    cmd = Command(
        "hlareforged",
        "--sample",
        args.sample,
        "--r1",
        args.r1,
        "--r2",
        args.r2,
        "--hla_ref",
        args.hlaref,
        "--outdir",
        args.wkdir,
        "--nproc",
        args.nproc,
        "--nproc_per_job",
        args.nproc_per_job,
    )
    if args.realign_only:
        cmd += ["--realn_only"]
    else:
        cmd += ["--freq", args.freq]

    return cmd


@jobfy
def run_hlapolysolver(args: argparse.Namespace):

    return Command(
        "hlapolysolver",
        "--sample",
        args.sample,
        "--bam",
        args.bam,
        "--nv_idx",
        args.nv_idx,
        "--bed",
        args.bed,
        "--tag",
        args.tag,
        "--freq",
        args.freq,
        "--out_bam",
        args.out_bam,
        "--nproc",
        args.nproc,
    )


def main() -> None:

    parser = parse_cmd()

    args = parser.parse_args()

    if not args.command:
        parser.print_help()

    if args.command == "polysolver":
        run_hlapolysolver(args)
    elif args.command == "hlareforged":
        run_hlareforged(args)
    else:
        raise ValueError(
            f"Unrecognized subcommand: {args.command}. ",
            "Supported commands: hlareforged, polysolver",
        )


if __name__ == "__main__":
    main()

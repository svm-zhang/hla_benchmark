from __future__ import annotations

import argparse

from command import Command

from cli import parse_cmd
from job import jobfy


@jobfy
def run_polysolvermod(args: argparse.Namespace):

    cmd = Command(
        "polysolvermod",
        "--sample",
        args.sample,
        "--bam",
        args.bam,
        "--hla_ref",
        args.hlaref,
        "--bed",
        args.bed,
        "--tag",
        args.tag,
        "--outdir",
        args.wkdir,
        "--fish_mode",
        args.fish_mode,
        "--nproc",
        args.nproc,
    )
    if args.realign_only:
        cmd += ["--realn_only"]
    else:
        cmd += ["--freq", args.freq]

    return cmd


def main() -> None:

    parser = parse_cmd()

    args = parser.parse_args()

    if not args.command:
        parser.print_help()

    if args.command == "polysolvermod":
        run_hlapolysolver(args)
    else:
        raise ValueError(
            f"Unrecognized subcommand: {args.command}. ",
            "Supported command: polysolvermod",
        )


if __name__ == "__main__":
    main()

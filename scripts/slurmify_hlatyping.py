from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import argparse
import sys

from command import Command, cook_hlareforge_cmd, cook_polysolver_cmd
from pathio import parse_path, make_dir, check_path, get_parent_dir


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
        "--freq",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA population frequency file",
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
    opti = commands.add_parser("opti", parents=[parent_parser])
    opti.add_argument(
        "--wkdir",
        metavar="DIR",
        type=parse_path,
        required=True,
        help="specify path to output directory",
    )
    opti.add_argument(
        "--hlaref",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA reference sequence in FASTA",
    )
    opti.add_argument(
        "--r1",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify R1 reads in FASTQ",
    )
    opti.add_argument(
        "--r2",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify R2 reads in FASTQ",
    )
    opti.set_defaults(func=slurmify_hlareforge)

    polysolver = commands.add_parser("polysolver", parents=[parent_parser])
    polysolver.add_argument(
        "--bam",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify BAM file",
    )
    polysolver.add_argument(
        "--out_bam",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify path to output realigned BAM file",
    )
    polysolver.add_argument(
        "--nv_idx",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA reference novoindex",
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
    polysolver.set_defaults(func=slurmify_polysolver)

    return parser


@dataclass
class Job:
    name: str
    resource: ResourceToAsk
    log: JobLog
    script: Path


@dataclass
class ResourceToAsk:
    nproc: int = 1
    ram: int = 4
    ntask: int = 1
    nodes: int = 1


@dataclass
class JobLog:
    stdout: Path
    stderr: Path
    donefile: Path
    failfile: Path


class JobHeader(Protocol):
    def make(self, job: Job) -> str:
        """Make job header section"""
        ...


class SlurmJobHeader:
    def make(self, job: Job) -> str:
        """Make job header section"""

        directive_prefix = "#SBATCH"
        header = ["#!/usr/bin/env bash\n"]
        header += [f'{directive_prefix} --job-name="{job.name}"']
        header += [f"{directive_prefix} --output={str(job.log.stdout)}"]
        header += [f"{directive_prefix} --error={str(job.log.stderr)}"]

        header += [f"{directive_prefix} --ntasks={job.resource.ntask}"]
        header += [f"{directive_prefix} --nodes={job.resource.nodes}"]
        header += [f"{directive_prefix} --cpus-per-task={job.resource.nproc}"]
        header += [f"{directive_prefix} --mem={job.resource.ram}G"]

        return "\n".join(header)


class SGEJobHeader:
    def make(self, job: Job) -> str:
        """Make job header section"""

        directive_prefix = "#$"
        header = []
        header += [f"{directive_prefix} -N {job.name}"]
        header += [f"{directive_prefix} -o {str(job.log.stdout)}"]
        header += [f"{directive_prefix} -e {str(job.log.stderr)}"]
        header += [f"{directive_prefix} -pe shm {job.resource.nproc / 2}"]
        header += [f"{directive_prefix} -l h_veme {job.resource.ram}G"]

        return "\n".join(header)


def setup_job(dir: Path, jobname: str, job_resource: ResourceToAsk) -> Job:

    joblog = setup_job_logfiles(dir=dir, fileprefix=jobname)
    jobscript = setup_job_script(
        dir=dir, scheduler="slurm", fileprefix=jobname
    )
    return Job(
        name=jobname, resource=job_resource, log=joblog, script=jobscript
    )


def setup_job_logfiles(dir: Path, fileprefix: str = "job") -> JobLog:

    logdir = dir / "log"
    make_dir(path=logdir, parents=True, exist_ok=True)
    stdout = logdir / f"{fileprefix}.stdout"
    stderr = logdir / f"{fileprefix}.stderr"
    donefile = logdir / f"{fileprefix}.done"
    failfile = logdir / f"{fileprefix}.fail"

    return JobLog(
        stdout=stdout, stderr=stderr, donefile=donefile, failfile=failfile
    )


def setup_job_script(
    dir: Path, fileprefix: str = "script", scheduler: str = "slurm"
) -> Path:
    jobdir = dir / "job"
    make_dir(path=jobdir, parents=True, exist_ok=True)

    if scheduler == "slurm":
        return jobdir / f"{fileprefix}.slurm"
    elif scheduler == "sge":
        return jobdir / f"{fileprefix}.sge"
    elif scheduler == "bash":
        return jobdir / f"{fileprefix}.sh"
    else:
        print("Unrecognized scheduler value")
        print("Supports: slurm, sge, and bash")
        sys.exit(1)


def add_rc_status_block(joblog: JobLog) -> str:
    return f"""
if [[ $? != 0 ]]; then
    touch {joblog.failfile}
    exit 1
else
    touch {joblog.donefile}
    exit 0
fi

    """


def make_jobscript(
    commands: list[Command],
    job: Job,
    scheduler: str = "slurm",
    overwrite: bool = False,
):

    header = ""
    if scheduler == "slurm":
        header = SlurmJobHeader().make(job=job)
    elif scheduler == "sge":
        header = SGEJobHeader().make_header(job=job)
    elif scheduler == "bash":
        header = "#!/usr/bin/env bash\n"
    else:
        print("Unrecognized scheduler value")
        print("Supports: slurm, sge, and bash")
        sys.exit(1)

    body = "\n".join([" ".join(command.args) for command in commands])

    tail = add_rc_status_block(joblog=job.log)

    content = [header, body, tail]

    if not job.script.exists() or overwrite or job.script.stat().st_size == 0:
        with open(job.script, "w") as fOUT:
            fOUT.write("\n\n".join(content))


def slurmify_polysolver(args: argparse.Namespace) -> None:

    check_path(path=args.bam, check_is_file=True, check_exists=True)

    jobname = f"hlapolysolver.{args.sample}"
    resource = ResourceToAsk(nproc=args.nproc, ram=args.ram)
    wkdir = get_parent_dir(p=args.out_bam)
    job = setup_job(dir=wkdir, jobname=jobname, job_resource=resource)
    cmd = cook_polysolver_cmd(
        sample=args.sample,
        bam=args.bam,
        nv_idx=args.nv_idx,
        bed=args.bed,
        tag=args.tag,
        freq=args.freq,
        outbam=args.out_bam,
    )

    make_jobscript(
        commands=[cmd],
        job=job,
        scheduler=args.scheduler,
        overwrite=args.overwrite,
    )


def slurmify_hlareforge(args: argparse.Namespace):

    check_path(path=args.r1, check_is_file=True, check_exists=True)
    check_path(path=args.r2, check_is_file=True, check_exists=True)

    jobname = f"hlareforged.{args.sample}"
    resource = ResourceToAsk(nproc=args.nproc, ram=args.ram)
    job = setup_job(dir=args.wkdir, jobname=jobname, job_resource=resource)

    cmd = cook_hlareforge_cmd(
        sample=args.sample,
        r1=args.r1,
        r2=args.r2,
        hlaref=args.hlaref,
        freq=args.freq,
        outdir=args.wkdir,
    )

    make_jobscript(
        commands=[cmd],
        job=job,
        scheduler=args.scheduler,
        overwrite=args.overwrite,
    )


def main() -> None:

    parser = parse_cmd()

    args = parser.parse_args()

    if args.func:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

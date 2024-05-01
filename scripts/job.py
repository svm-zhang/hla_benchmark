from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from command import Command
from pathio import make_dir, get_parent_dir

import argparse


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
        header = ["#!/usr/bin/env bash\n"]
        header += [f"{directive_prefix} -N {job.name}"]
        header += [f"{directive_prefix} -o {str(job.log.stdout)}"]
        header += [f"{directive_prefix} -e {str(job.log.stderr)}"]
        header += [f"{directive_prefix} -pe shm {int(job.resource.nproc / 2)}"]
        header += [f"{directive_prefix} -l h_veme {job.resource.ram}G"]

        return "\n".join(header)


def setup_job(
    dir: Path,
    jobname: str,
    job_resource: ResourceToAsk,
    scheduler: str = "slurm",
) -> Job:

    joblog = setup_job_logfiles(dir=dir, fileprefix=jobname)
    jobscript = setup_job_script(
        dir=dir, scheduler=scheduler, fileprefix=jobname
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
        raise ValueError(
            "Unrecognized scheduler value. Supports: slurm, sge, and bash"
        )


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
        header = SGEJobHeader().make(job=job)
    elif scheduler == "bash":
        header = "#!/usr/bin/env bash\n"
    else:
        raise ValueError(
            "Unrecognized scheduler value. Supports: slurm, sge, and bash"
        )

    body = "\n".join([" ".join(command.args) for command in commands])

    tail = add_rc_status_block(joblog=job.log)

    content = [header, body, tail]

    if not job.script.exists() or overwrite or job.script.stat().st_size == 0:
        with open(job.script, "w") as fOUT:
            fOUT.write("\n\n".join(content))


def jobfy(func):
    def wrapper(args: argparse.Namespace):
        jobname = f"{args.command}.{args.sample}"
        resource = ResourceToAsk(nproc=args.nproc, ram=args.ram)
        wkdir: Path = None
        if args.command == "hlareforged":
            wkdir = args.wkdir
        else:
            wkdir = get_parent_dir(p=args.out_bam)
        job = setup_job(
            dir=wkdir,
            jobname=jobname,
            job_resource=resource,
            scheduler=args.scheduler,
        )

        cmd = func(args)

        make_jobscript(
            commands=[cmd],
            job=job,
            scheduler=args.scheduler,
            overwrite=args.overwrite,
        )

    return wrapper

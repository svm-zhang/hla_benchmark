from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path, PosixPath
from typing import Optional

import argparse
import sys


@dataclass
class JobLog:
    done: Path
    fail: Path
    stdout: Path
    stderr: Path


def setup_job_log_files(logdir: Path, job_name: str) -> JobLog:

    make_dir(path=logdir, parents=True, exist_ok=True)

    joblog = JobLog(
        done=logdir / f"{job_name}.done",
        fail=logdir / f"{job_name}.fail",
        stdout=logdir / f"{job_name}.stdout",
        stderr=logdir / f"{job_name}.stderr",
    )

    return joblog


def parse_cmd() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        metavar="STR",
        type=str,
        required=True,
        help="specify sample ID",
    )
    parser.add_argument(
        "--wkdir",
        metavar="DIR",
        type=parse_path,
        required=True,
        help="specify path to output directory",
    )
    parser.add_argument(
        "--freq",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA population frequency file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="specify whether or not to overwrite job file",
    )
    commands = parser.add_subparsers(title="Commands", dest="command")

    opti = commands.add_parser("opti")
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

    polysolver = commands.add_parser("polysolver")
    polysolver.add_argument(
        "--bam",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify BAM file",
    )
    polysolver.add_argument(
        "--genome",
        metavar="FILE",
        type=parse_path,
        required=True,
        help="specify HLA reference sequence in FASTA",
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


class Command:
    """Representation of command

    A Command object is represented by a list of arguments
    (str). It is defined with various operations including
    + (append), | (pipe), > (STDOUT direct), >> (STDOUT append),
    2> (STDERR direct), 2>> (STDERR append), 2>&1 (redirect STDERR
    to STDOUT), 1>&2 (redirect STDOUT to STDERR).

    Attributes
    ----------

    args : list of str
        list of arguments in a Command object

    """

    def __init__(self, *args: CmdArg) -> None:
        self.__args = args

    @property
    def args(self) -> list[str]:
        """Return command arguments

        Returns
        -------

        list of str

        """

        if isinstance(self.__args, str):
            self.__args = self.__split(self.__args)

        # Make sure Path object converted to string literal
        return [
            arg if isinstance(arg, str) else str(arg) for arg in self.__args
        ]

    def __add__(self, cmd2: Command | list[CmdArg]) -> Command:
        """Append command arguments

        Overriding the build-in + operation

        Parameters
        ----------

        cmd2 : Command or list of CmdArg
            The Command or argument to be appended to the current command

        Returns
        -------

        Command object

        """

        cmd1 = self

        if not isinstance(cmd2, Command):
            cmd2 = Command(*cmd2)

        return Command(*cmd1.args, *cmd2.args)

    def __or__(self, cmd2: Command) -> Command:
        """Pipe one command to the next

        Overriding the built-in Bitwise | operation

        Parameters
        ----------

        cmd2 : Command
            Command object that the current Command pipes to

        Returns
        -------

        Command object

        """

        return self + Command("|") + cmd2

    def __split(self, cmd: str) -> list[str]:
        """Split command string into a list of strings

        Parameters
        ----------

        cmd : str
            command string literal

        Returns
        -------

        list of str

        Examples
        --------

        >>>cmd = "bwa mem -M -t 8 reference.fa r1.fq.gz r2.fq.gz"
        >>>Command.__split(cmd=cmd)
        ["bwa", "mem", "-M", "-t" "8", "reference.fa", "r1.fq.gz", "r2.fq.gz"]

        """

        return shlex.split(cmd)

    def direct_to_stdout(
        self, stdout: Path, *, append: bool = False
    ) -> Command:
        """Direct to STDOUT

        Parameters
        ----------

        stdout : Path
            Path object to a file hosing STDOUT

        append : bool, default False
            Specify to append mode (>>)

        Returns
        -------

        Command object

        """

        rd = ">" if not append else ">>"

        return self + Command(f"{rd}", stdout)

    def direct_to_stderr(
        self, stderr: Path, *, append: bool = False
    ) -> Command:
        """Direct to STDERR

        Parameters
        ----------

        stderr : Path
            Path object to a file hosing STDERR

        append : bool, default False
            Specify to append mode (2>>)

        Returns
        -------

        Command object

        """

        rd = ">" if not append else ">>"

        return self + Command(f"2{rd}", stderr)

    def redirect_stdout_to_stderr(self) -> Command:
        """Redirect STDOUT stream to STDERR by 1>&2

        Returns
        -------

        Command object

        """

        return self + Command(">&2")

    def redirect_stderr_to_stdout(self) -> Command:
        """Redirect STDERR stream to STDOUT by 2>&1

        Returns
        -------

        Command object

        """

        return self + Command("2>&1")


def parse_path(
    path: PathLike,
    *,
    expanduser: bool = True,
) -> Path:
    """Parse a given path.

    Input path can be either a Path or string type

    This function will convert all non-Path type path
    to Path type. If the given path is PosixPath type,
    the returned path will be expanded and be absolute
    by default.

    Parameters
    ----------

    path : PathLike
        Path object or string to a give path

    expanduser : bool, default True
        Specify to expand a PosixPath path, e.g. ~

    Returns
    -------

    Path object

    See Also
    --------

    pathlib : https://docs.python.org/3/library/pathlib.html

    Examples
    --------

    [WIP]

    """
    p: Path
    if isinstance(path, Path):
        p = path
    elif isinstance(path, str) and (
        path.startswith("s3:") or path.startswith("gcs:")
    ):
        raise ValueError(f"Cloud-based path is not supported: {path}")
    else:
        p = Path(path)

    if isinstance(p, PosixPath):
        if expanduser:
            p = p.expanduser()
        p = p.resolve()

    return p


def check_path(
    path: PathLike,
    check_is_file: bool = False,
    check_is_dir: bool = False,
    check_exists: bool = False,
) -> None:
    """Check a given path

    Check if a given path is a file or
    is a directory or exists. Because a path
    can only point to either a file or a directory,
    the function will fail when checking a path for
    both

    This function only works on Unix- and
    POSIX-compatiable path

    Parameters
    ----------

    path : PathLike
        Path object or string to a give path

    check_is_file : bool, default False
        Specify to check if a path points to a file

    check_is_dir : bool, default False
        Specify to check if a path points to a dir

    check_exists : bool, default False
        Specify to check if a path exists

    Returns
    -------

    None

    See Also
    --------

    pathlib.Path : https://docs.python.org/3/library/pathlib.html

    Examples
    --------


    """
    if check_is_file and check_is_dir:
        raise ValueError(
            "A given path can point to either a file or a directory. Not both"
        )

    if not isinstance(path, Path):
        path = parse_path(path)

    if not isinstance(path, PosixPath):
        raise ValueError(
            f"Only Unix and POSIX-compatible paths are allowed: {path}"
        )

    if check_is_file and not path.is_file():
        raise ValueError(f"Path does not point to a regular file: {path}")

    if check_is_dir and not path.is_dir():
        raise ValueError(f"Path does not point to a directory: {path}")

    if check_exists and not path.exists():
        raise OSError(f"Path provided does not exist: {path}")


def make_dir(
    path: Path,
    *,
    mode: int = 511,
    parents: bool = False,
    exist_ok: bool = False,
) -> None:
    """Make directory

    Parameters
    ----------

    path : PathLike
        Path object or string to a give path

    mode : int, default 511
        Determine file mode and access flag
        by combining umask value

    parents : bool, default False
        Specify to create any missing parents
        in the path

    exists_ok : bool, default False
        Specify to allow target directory given
        by the path to exist

    Returns
    -------

    None

    See Also
    --------

    pathlib.Path.mkdir : https://docs.python.org/3/library/pathlib.html

    """

    if not isinstance(path, Path):
        path = parse_path(path)

    if not path.exists():
        path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)


def get_parent_dir(p: Path, level: int = 0) -> Path:

    parent_dirs = p.parents

    if level > len(parent_dirs):
        raise ValueError(
            (
                f"level {level} cannot beyond the number of logical ancestors "
                f"of the given path: {len(parent_dirs)}"
            )
        )

    return parent_dirs[level]


def add_header(
    scheduler: str,
    job_name: str,
    stdout: Path,
    stderr: Path,
    *,
    threads: int = 1,
    ram: int = 4,
) -> str:
    Header = namedtuple(
        "Header", ["ncore", "ram", "job_name", "stdout", "stderr"]
    )

    header = []
    if scheduler == "slurm":
        ncore = int(threads) if threads > 0 else 1
        H = Header(
            ncore=ncore,
            ram=ram,
            job_name=job_name,
            stdout=stdout,
            stderr=stderr,
        )
        header += [f'#SBATCH --job-name="{H.job_name}"']
        header += [f"#SBATCH --output={str(H.stdout)}"]
        header += [f"#SBATCH --error={str(H.stderr)}"]

        header += ["#SBATCH --ntasks=1"]
        header += [f"#SBATCH --cpus-per-task={H.ncore}"]
        header += [f"#SBATCH --mem={H.ram}G"]

    elif scheduler == "pbs":
        raise ValueError("no pbs job support yet")

    elif scheduler == "sge":
        H = Header(
            ncore=threads / 2,
            ram=ram,
            job_name=job_name,
            stdout=stdout,
            stderr=stderr,
        )

        header += [f"#$ -N {H.job_name}"]
        header += [f"#$ -o {str(H.stdout)}"]
        header += [f"#$ -e {str(H.stderr)}"]

        header += [f"#$ -pe shm {H.ncore}"]
        header += [f"#$ -l h_vmem={H.ram}G"]

    return "\n".join(header)


def add_command(command: list[str]) -> str:
    return " ".join(command)


def add_rc_status_block(done: Path, fail: Path) -> str:
    return f"""
if [[ $? != 0 ]]; then
    touch {fail}
    exit 1
else
    touch {done}
    exit 0
fi

    """


def to_job(
    command: list[str],
    threads: int,
    ram: int,
    job_name: str,
    joblog: JobLog,
    outdir: Path,
    *,
    overwrite: bool = False,
    scheduler: str = "slurm",
) -> Path:
    job_str = ["#!/usr/bin/env bash"]

    # FIXME: forget about pbs for now
    if scheduler != "native":
        job_str += [
            add_header(
                scheduler=scheduler,
                job_name=job_name,
                stdout=joblog.stdout,
                stderr=joblog.stderr,
                threads=threads,
                ram=ram,
            )
        ]

    job_str += [add_command(command=command)]

    job_str += [add_rc_status_block(done=joblog.done, fail=joblog.fail)]

    # FIXME: fix suffix scope
    if scheduler == "native":
        suffix = ".sh"

    elif scheduler == "slurm":
        suffix = ".slurm"

    elif scheduler == "pbs":
        suffix = ".pbs"

    else:
        suffix = ".sge"

    job_file = outdir / f"{job_name}{suffix}"

    if not job_file.exists() or overwrite:
        with open(job_file, "w") as fOUT:
            fOUT.write("\n\n".join(job_str))

    return job_file


def make_hlareforge(
    sample: str,
    r1: Path,
    r2: Path,
    hlaref: Path,
    freq: Path,
    outdir: Path,
    race: str = "Unknown",
    joblog: Optional[JobLog] = None,
) -> Command:
    cmd = Command(
        "hlatyping",
        "--sample",
        sample,
        "--r1",
        r1,
        "--r2",
        r2,
        "--hla_ref",
        hlaref,
        "--freq",
        freq,
        "--race",
        race,
        "--outdir",
        outdir,
    )

    if joblog is not None:
        cmd = cmd.direct_to_stdout(stdout=joblog.stdout)
        cmd = cmd.direct_to_stderr(stderr=joblog.stderr)

    return cmd


def make_polysolver(
    sample: str,
    bam: Path,
    genome: Path,
    nv_idx: Path,
    bed: Path,
    tag: Path,
    freq: Path,
    outdir: Path,
    race: str = "Unknown",
    joblog: Optional[JobLog] = None,
) -> Command:
    cmd = Command(
        "jspolysolver",
        "--sample",
        sample,
        "--bam",
        bam,
        "--genome",
        genome,
        "--nv_idx",
        nv_idx,
        "--bed",
        bed,
        "--tag",
        tag,
        "--freq",
        freq,
        "--race",
        race,
        "--outdir",
        outdir,
    )

    if joblog is not None:
        cmd = cmd.direct_to_stdout(stdout=joblog.stdout)
        cmd = cmd.direct_to_stderr(stderr=joblog.stderr)

    return cmd


def slurmify_polysolver(args: argparse.Namespace) -> None:

    check_path(path=args.bam, check_is_file=True, check_exists=True)
    outdir = args.wkdir / "polysolver_hlatyping"

    job_name = f"polysolver.{args.sample}"
    joblog = setup_job_log_files(
        logdir=args.wkdir / "log_test", job_name=job_name
    )
    job_dir = args.wkdir / "job_test"
    make_dir(path=job_dir, parents=True, exist_ok=True)

    cmd = make_polysolver(
        sample=args.sample,
        bam=args.bam,
        genome=args.genome,
        nv_idx=args.nv_idx,
        bed=args.bed,
        tag=args.tag,
        freq=args.freq,
        outdir=outdir,
        joblog=joblog,
    )

    to_job(
        command=cmd.args,
        threads=8,
        ram=12,
        job_name=job_name,
        joblog=joblog,
        outdir=job_dir,
        overwrite=args.overwrite,
    )


def slurmify_hlareforge(args: argparse.Namespace):

    check_path(path=args.r1, check_is_file=True, check_exists=True)
    check_path(path=args.r2, check_is_file=True, check_exists=True)
    outdir = args.wkdir / "test"

    job_name = f"hlatyping.{args.sample}"
    joblog = setup_job_log_files(
        logdir=args.wkdir / "log_test", job_name=job_name
    )
    job_dir = args.wkdir / "job_test"
    make_dir(path=job_dir, parents=True, exist_ok=True)

    cmd = make_hlatyping(
        sample=args.sample,
        r1=args.r1,
        r2=args.r2,
        hlaref=args.hlaref,
        freq=args.freq,
        outdir=outdir,
        joblog=joblog,
    )

    to_job(
        command=cmd.args,
        threads=8,
        ram=12,
        job_name=job_name,
        joblog=joblog,
        outdir=job_dir,
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

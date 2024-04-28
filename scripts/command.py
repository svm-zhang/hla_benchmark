from __future__ import annotations

from pathlib import Path

import shlex

CmdArg = str | int | bool | float | Path


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


def cook_hlareforge_cmd(
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
        "bash",
        "/data/simo/resource/1kg/hlatypingReforged/scripts/hlareforged.sh",
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
        "--outdir",
        outdir,
    )

    if joblog is not None:
        cmd = cmd.direct_to_stdout(stdout=joblog.stdout)
        cmd = cmd.direct_to_stderr(stderr=joblog.stderr)

    return cmd

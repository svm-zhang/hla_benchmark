from __future__ import annotations

from pathlib import Path, PosixPath


def parse_path(
    path: Path | str,
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
    path: Path | str,
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

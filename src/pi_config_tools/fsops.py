"""File and tree copies with exclusions (stdlib only)."""

import fnmatch
import os
import shutil
from pathlib import Path

# Name-based exclusions, applied at any depth (repo-side rules)
EXCLUDE_DIRS = {"node_modules", "sessions", "__pycache__", ".venv", ".git"}
EXCLUDE_FILE_PATTERNS = [
    "auth.json",
    "*.bak*",
    "settings.backup*",
    "mcp-cache.json",
    "run-history.jsonl",
    "*.pyc",
]


def copy_tree(
    src: Path,
    dst: Path,
    exclude_dirs: set[str] | None = None,
    exclude_files: list[str] | None = None,
) -> int:
    """Recursively copy src -> dst applying the exclusions (default: repo rules).
    Returns the number of files copied."""
    if exclude_dirs is None:
        exclude_dirs = EXCLUDE_DIRS
    if exclude_files is None:
        exclude_files = EXCLUDE_FILE_PATTERNS
    count = 0
    for item in src.iterdir():
        if item.is_dir():
            if item.name in exclude_dirs:
                continue
            count += copy_tree(item, dst / item.name, exclude_dirs, exclude_files)
        elif item.is_file():
            if any(fnmatch.fnmatch(item.name, pat) for pat in exclude_files):
                continue
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst / item.name)
            count += 1
    return count


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


class SwapError(OSError):
    """`swap_dir` could not install the staging tree, and where things landed.

    `target_intact` is measured after the failure, never assumed: a caller must
    not tell the operator the target was left unchanged unless this says so.
    `aside` and `staging` name the trees still on disk, so the message can
    carry a recovery path instead of a shrug.
    """

    def __init__(
        self,
        message: str,
        *,
        target_intact: bool,
        aside: Path | None = None,
        staging: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.target_intact = target_intact
        self.aside = aside
        self.staging = staging


def swap_dir(staging: Path, target: Path) -> Path | None:
    """Install `staging` as `target`, keeping the old content until the swap lands.

    Three renames instead of a delete-then-rebuild: move the old target aside,
    move the staging in, drop the aside copy. Each phase fails safe.

    - the first rename raises  -> the target is untouched, nothing is lost;
    - the second rename raises -> the aside copy is put back, then the error
      propagates, so the caller never sees a half-installed target;
    - both raise               -> the target is gone and `SwapError.aside`
      says where the previous snapshot is; the two errors are chained so
      neither phase is hidden behind the other;
    - the aside copy is removed only once the new target is in place.

    `os.replace` is used rather than `Path.rename` because it must not fail on
    an existing name, and directory-to-directory: on Windows replacing a
    non-empty directory raises WinError 5, which is exactly why the old target
    is renamed away first instead of being overwritten in place.

    NOT strictly atomic, and the docstring says so on purpose: the second
    rename and the rollback are themselves syscalls that can fail (an open
    handle anywhere under the tree is enough on Windows). This narrows the
    unsafe window to a single rename; it does not remove it.

    Returns the leftover aside path when it could not be removed, else None.
    """
    aside = target.with_name(f"{target.name}.old-{os.getpid()}")
    had_target = target.exists()
    if had_target:
        try:
            os.replace(target, aside)
        except OSError as exc:
            raise SwapError(
                f"could not move the previous {target} aside ({exc})",
                target_intact=target.exists(),
                staging=staging,
            ) from exc
    try:
        os.replace(staging, target)
    except OSError as install_exc:
        if not had_target:
            raise SwapError(
                f"could not install {staging} as {target} ({install_exc})",
                target_intact=False,
                staging=staging,
            ) from install_exc
        try:
            os.replace(aside, target)
        except OSError as rollback_exc:
            raise SwapError(
                f"could not install {staging} as {target} ({install_exc}), and "
                f"putting the previous snapshot back failed too ({rollback_exc})",
                target_intact=target.exists(),
                aside=aside,
                staging=staging,
            ) from rollback_exc
        raise SwapError(
            f"could not install {staging} as {target} ({install_exc}); "
            "the previous snapshot was put back",
            target_intact=target.exists(),
            staging=staging,
        ) from install_exc
    if not had_target:
        return None
    shutil.rmtree(aside, ignore_errors=True)
    return aside if aside.exists() else None

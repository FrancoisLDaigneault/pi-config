"""Replacing a directory with a freshly built one, and the aftermath (stdlib only).

One subject, not two: `swap_dir` is not atomic on Windows, so the trees it
leaves behind when a run dies mid-swap are part of the same protocol. The
staging and aside names are minted here and read back here -- a recovery
living anywhere else would be guessing at a convention it does not own.

Every tree named here is gitignored, so `git status` stays silent about all
of them: nothing but this module will tell the operator config/ is gone.
"""

import os
import shutil
from pathlib import Path


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


def staging_for(target: Path) -> Path:
    """The transient build tree for `target`, beside it and tagged with the pid.

    Beside it so the swap below is a rename on the same volume rather than a
    cross-device copy, and pid-tagged so two runs never build into the same
    tree.
    """
    return target.with_name(f".{target.name}-staging-{os.getpid()}")


def report_stale_stagings(target: Path) -> None:
    """Name build trees that are not this run's. Never remove them.

    A run killed between building and swapping leaves its staging tree, and it
    is gitignored like the aside copy, so `git status` stays silent while they
    accumulate. Deleting one from here would be worse than leaving it: the pid
    in the name may belong to a sync running right now, or to a process whose
    pid has since been reused. Naming it lets the operator decide.

    The message says so too. Calling every foreign tree the leftover of a
    finished run and telling the operator to delete it is advice that destroys
    a concurrent run's work, which is exactly what this function refuses to do
    itself.
    """
    mine = staging_for(target).name
    for path in sorted(target.parent.glob(f".{target.name}-staging-*")):
        if path.name != mine:
            print(f"  warning: another or a previous run left a build tree at {path}")
            print("  it is gitignored, so nothing else will mention it; make sure no other")
            print("  sync is running, then remove it by hand")


def recover_interrupted_swap(config: Path) -> str | None:
    """Put back a snapshot a previous run was killed in the middle of moving.

    Between the two renames of `swap_dir` the target is absent and the previous
    snapshot sits under `<name>.old-<token>`. Both that and the staging tree
    are gitignored, so `git status` shows nothing and nothing else would tell
    the operator config/ is gone. Returns an error message, or None when there
    is nothing to do or the recovery succeeded.
    """
    if config.exists():
        return None
    asides = sorted(config.parent.glob(f"{config.name}.old-*"))
    if not asides:
        return None
    if len(asides) > 1:
        listed = "\n    ".join(str(path) for path in asides)
        return (
            f"{config} is missing and several previous snapshots were left behind:\n"
            f"    {listed}\n"
            "  pick the one to keep and rename it to config, by hand: sync will\n"
            "  not choose between them for you"
        )
    os.replace(asides[0], config)
    print(f"  recovered {config} from {asides[0].name} (a previous sync was interrupted)")
    return None


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
    aside = target.with_name(f"{target.name}.old-{os.urandom(4).hex()}")
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

"""Consistent snapshots of SQLite databases (stdlib only).

Copying a live database file by file is not a backup. A WAL-mode database is
several files, and a checkpoint landing between two `copy2` calls drops
committed transactions while `PRAGMA integrity_check` still answers `ok` --
measured, not theoretical, so the loss is silent. `Connection.backup` takes the
snapshot under SQLite's own locks instead, and folds the WAL content in.

The presence of a `-wal` file is therefore not an error and must not fail a
backup: it is the normal state of a live database.
"""

import shutil
import sqlite3
import time
from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
# How long a single lock wait may last. It does NOT bound the whole copy:
# measured, a backup of a database held under BEGIN EXCLUSIVE waited the full
# 90 s the lock was held despite timeout=5.
BUSY_TIMEOUT_S = 5.0
# What actually bounds the copy. Checked between batches, so the real ceiling
# is this plus one batch; without it a stuck writer stalls the whole backup
# for as long as it likes.
DEADLINE_S = 60.0
BATCH_PAGES = 256


def is_sqlite(path: Path) -> bool:
    """True when the file really is a SQLite database, by header magic.

    Read rather than trusted from the extension: MemPalace holds plain files
    next to its databases, and a `.sqlite3` name proves nothing.
    """
    try:
        with path.open("rb") as handle:
            return handle.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC
    except OSError:
        return False


def sidecar_parent(path: Path) -> Path | None:
    """The database a -wal/-shm/-journal companion belongs to, or None.

    Judged by name alone, so the caller must still check that the parent is a
    database it actually snapshotted. A suffix is not a sidecar: a plain file
    named `notes-journal` has a parent that does not exist, and dropping it
    from a backup on the strength of its name loses data silently.
    """
    for suffix in SIDECAR_SUFFIXES:
        if path.name.endswith(suffix):
            return path.with_name(path.name[: -len(suffix)])
    return None


def backup_db(
    src: Path,
    dst: Path,
    *,
    busy_timeout_s: float = BUSY_TIMEOUT_S,
    deadline_s: float = DEADLINE_S,
) -> None:
    """Snapshot `src` into `dst` while the source stays live.

    The source is opened read-only through a file: URI, so a corrupt path can
    never be created by the backup itself, and `Connection.backup` serialises
    against writers rather than racing them.

    The copy runs in batches with a deadline checked between them, because the
    connect timeout does not bound `backup()`: a writer holding the database
    kept it waiting for the whole lock, not for `busy_timeout_s`. A stuck
    writer now fails the section instead of hanging the backup, and SQLite
    leaves no half-written snapshot behind when the deadline fires.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"{src.as_uri()}?mode=ro", uri=True, timeout=busy_timeout_s)
    try:
        target = sqlite3.connect(dst, timeout=busy_timeout_s)
        deadline = time.monotonic() + deadline_s

        def stop_if_late(_status: int, remaining: int, total: int) -> None:
            if time.monotonic() > deadline:
                copied = total - remaining
                raise TimeoutError(
                    f"{src} was still locked after {deadline_s:g}s "
                    f"({copied} of {total} pages copied)"
                )

        try:
            source.backup(target, pages=BATCH_PAGES, progress=stop_if_late)
        finally:
            target.close()
    finally:
        source.close()


def _snapshot_databases(entries: list[Path], dst: Path) -> set[str]:
    """Take every database in `entries`, and name the ones actually taken.

    Only the names returned may have their companions dropped later, so a file
    that stopped being a database before it could be snapshotted must not be
    listed here: it is left to the copying pass, which reads it again.
    """
    snapshotted: set[str] = set()
    for item in entries:
        if not (item.is_file() and is_sqlite(item)):
            continue
        try:
            backup_db(item, dst / item.name)
        except sqlite3.DatabaseError:
            if is_sqlite(item):
                raise
            continue  # no longer a database: the second pass copies it plainly
        snapshotted.add(item.name)
    return snapshotted


def _take(item: Path, target: Path) -> bool:
    """Copy one file, snapshotting it when it is a database *at copy time*.

    Returns True when it was taken as a database snapshot.

    Reading the header and copying the file cannot be made one atomic step,
    and re-reading the source does not close that window -- it only narrows it
    to two adjacent calls. So the plain copy is judged afterwards, on what
    landed rather than on what was predicted, and a database that arrived that
    way is removed instead of kept: copied file by file it answers `ok` to an
    integrity check while holding none of the rows its WAL still carries.

    A file that stopped being a database before it could be snapshotted is
    copied for what it now is, and that error is swallowed only once the copy
    confirms the type really changed -- a database still refusing to be
    snapshotted is a genuine failure and must not be hidden behind a plain
    copy. When the copy refutes it, that original error is raised again rather
    than replaced, because it is the failure that actually happened.
    """
    cause: sqlite3.DatabaseError | None = None
    if is_sqlite(item):
        try:
            backup_db(item, target)
            return True
        except sqlite3.DatabaseError as exc:
            if is_sqlite(item):
                raise
            cause = exc
    shutil.copy2(item, target)
    if not is_sqlite(target):
        return False
    target.unlink()
    if cause is not None:
        raise cause
    raise sqlite3.DatabaseError(
        f"{item} was a plain file when its header was read and a database when it "
        "was copied, so the copy holds none of the rows its WAL still carries"
    )


def snapshot_tree(src: Path, dst: Path) -> tuple[int, int]:
    """Copy `src` into `dst`, snapshotting databases instead of copying them.

    A companion of a snapshotted database is skipped on purpose: `backup_db`
    folds the WAL into the snapshot, so copying it alongside would put back
    exactly the torn state this module exists to avoid. Every other file is
    copied, including one whose name merely ends in a sidecar suffix.

    Databases are taken first so that decision never depends on the order
    `iterdir` happens to return. That first pass decides which companions may
    be dropped; it does NOT decide how the remaining files are copied. Each one
    is read again by `_take` at the moment it is copied, because a file that
    was ordinary when the pass started and is a live database by the time it is
    reached would otherwise be copied without its WAL -- measured, the result
    answered `ok` to an integrity check and had lost the table entirely.

    Returns (files written, databases snapshotted).
    """
    entries = sorted(src.iterdir())
    snapshotted = _snapshot_databases(entries, dst)
    files = databases = len(snapshotted)
    for item in entries:
        target = dst / item.name
        if item.is_dir():
            sub_files, sub_databases = snapshot_tree(item, target)
            files += sub_files
            databases += sub_databases
        elif item.is_file() and item.name not in snapshotted:
            parent = sidecar_parent(item)
            if parent is not None and parent.name in snapshotted:
                continue
            dst.mkdir(parents=True, exist_ok=True)
            if _take(item, target):
                # Sorted order puts a database before its companions, so one
                # promoted here still shields its own -wal from a plain copy.
                snapshotted.add(item.name)
                databases += 1
            files += 1
    return files, databases

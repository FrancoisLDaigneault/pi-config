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


def snapshot_tree(src: Path, dst: Path) -> tuple[int, int]:
    """Copy `src` into `dst`, snapshotting databases instead of copying them.

    A companion of a snapshotted database is skipped on purpose: `backup_db`
    folds the WAL into the snapshot, so copying it alongside would put back
    exactly the torn state this module exists to avoid. Every other file is
    copied, including one whose name merely ends in a sidecar suffix.

    Databases are taken first so that decision never depends on the order
    `iterdir` happens to return.

    Returns (files written, databases snapshotted).
    """
    entries = sorted(src.iterdir())
    files = databases = 0
    snapshotted: set[str] = set()
    for item in entries:
        if item.is_file() and is_sqlite(item):
            backup_db(item, dst / item.name)
            snapshotted.add(item.name)
            files += 1
            databases += 1
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
            shutil.copy2(item, target)
            files += 1
    return files, databases

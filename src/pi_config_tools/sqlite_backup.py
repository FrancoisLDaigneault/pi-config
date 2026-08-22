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
from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
# A live writer holds the lock for milliseconds; this is a stall guard, not a
# retry policy. Exceeding it is a real failure and must surface as one.
BUSY_TIMEOUT_S = 5.0


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


def is_sidecar(path: Path) -> bool:
    """True for the -wal/-shm/-journal companions of a database."""
    return path.name.endswith(SIDECAR_SUFFIXES)


def backup_db(src: Path, dst: Path) -> None:
    """Snapshot `src` into `dst` while the source stays live.

    The source is opened read-only through a file: URI, so a corrupt path can
    never be created by the backup itself, and `Connection.backup` serialises
    against writers rather than racing them.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"{src.as_uri()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_S)
    try:
        target = sqlite3.connect(dst, timeout=BUSY_TIMEOUT_S)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def snapshot_tree(src: Path, dst: Path) -> tuple[int, int]:
    """Copy `src` into `dst`, snapshotting databases instead of copying them.

    Sidecars are skipped on purpose: `backup_db` folds the WAL into the
    snapshot, so copying the companions alongside would put back exactly the
    torn state this module exists to avoid.

    Returns (files written, databases snapshotted).
    """
    files = databases = 0
    for item in sorted(src.iterdir()):
        target = dst / item.name
        if item.is_dir():
            sub_files, sub_databases = snapshot_tree(item, target)
            files += sub_files
            databases += sub_databases
        elif item.is_file():
            if is_sidecar(item):
                continue
            if is_sqlite(item):
                backup_db(item, target)
                databases += 1
            else:
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
            files += 1
    return files, databases

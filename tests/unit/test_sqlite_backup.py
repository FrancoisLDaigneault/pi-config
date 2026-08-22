"""Unit tests for the SQLite-aware snapshot (everything in tmp_path)."""

import shutil
import sqlite3
from pathlib import Path

from pi_config_tools.sqlite_backup import backup_db, is_sidecar, is_sqlite, snapshot_tree


def _wal_db(path: Path, rows: int = 3) -> None:
    """A WAL-mode database, cleanly closed: SQLite folds the WAL back in."""
    _live_wal_db(path, rows).close()


def _live_wal_db(path: Path, rows: int = 3) -> sqlite3.Connection:
    """Same database, connection left OPEN so the -wal stays live on disk.

    Closing the last connection checkpoints and deletes the -wal, so a fixture
    that closes can never reproduce a running Pi. The caller must close.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE t (v TEXT)")
    con.executemany("INSERT INTO t VALUES (?)", [(f"row-{i}",) for i in range(rows)])
    con.commit()
    return con


def _rows(path: Path) -> int:
    con = sqlite3.connect(path)
    try:
        return int(con.execute("SELECT count(*) FROM t").fetchone()[0])
    finally:
        con.close()


def test_is_sqlite_reads_the_header_not_the_extension(tmp_path: Path) -> None:
    real = tmp_path / "real.sqlite3"
    _wal_db(real)
    impostor = tmp_path / "impostor.sqlite3"
    impostor.write_text("db", encoding="utf-8")

    assert is_sqlite(real)
    assert not is_sqlite(impostor), "a .sqlite3 name proves nothing about the content"
    assert not is_sqlite(tmp_path / "absent.sqlite3")


def test_is_sidecar_covers_the_three_companions() -> None:
    assert is_sidecar(Path("k.sqlite3-wal"))
    assert is_sidecar(Path("k.sqlite3-shm"))
    assert is_sidecar(Path("k.sqlite3-journal"))
    assert not is_sidecar(Path("k.sqlite3"))


def test_backup_db_snapshots_a_live_wal_database(tmp_path: Path) -> None:
    src = tmp_path / "live.sqlite3"
    con = _live_wal_db(src, rows=5)
    try:
        assert (tmp_path / "live.sqlite3-wal").exists(), "the fixture must leave a live WAL"
        dst = tmp_path / "out" / "live.sqlite3"
        backup_db(src, dst)
    finally:
        con.close()

    assert _rows(dst) == 5


def test_backup_db_survives_a_checkpoint_that_breaks_a_file_copy(tmp_path: Path) -> None:
    """The exact interleaving that loses committed rows through copy2.

    A checkpoint between copying the database and copying its WAL truncates the
    WAL, and the file-by-file copy answers `ok` to integrity_check while the
    table has vanished. The snapshot must not have that failure mode.
    """
    src = tmp_path / "live.sqlite3"
    con = _live_wal_db(src, rows=4)
    wal = tmp_path / "live.sqlite3-wal"
    naive = tmp_path / "naive.sqlite3"
    snapshot = tmp_path / "snapshot.sqlite3"
    try:
        # 1. the naive copy, with a checkpoint landing between the two files
        shutil.copy2(src, naive)
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copy2(wal, tmp_path / "naive.sqlite3-wal")
        # 2. the snapshot, on the same live database
        backup_db(src, snapshot)
    finally:
        con.close()

    naive_con = sqlite3.connect(naive)
    try:
        assert naive_con.execute("PRAGMA integrity_check").fetchone() == ("ok",), (
            "integrity_check answering ok is what makes the loss silent"
        )
        try:
            lost = int(naive_con.execute("SELECT count(*) FROM t").fetchone()[0])
        except sqlite3.DatabaseError:
            lost = -1  # the table did not survive at all
    finally:
        naive_con.close()
    assert lost != 4, "the naive copy is expected to lose committed rows here"
    assert _rows(snapshot) == 4


def test_snapshot_tree_skips_sidecars_and_keeps_plain_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _wal_db(src / "graph.sqlite3", rows=2)
    (src / "notes.md").write_text("plain", encoding="utf-8")
    _wal_db(src / "nested" / "second.sqlite3", rows=7)

    dst = tmp_path / "dst"
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (3, 2)
    assert _rows(dst / "graph.sqlite3") == 2
    assert _rows(dst / "nested" / "second.sqlite3") == 7
    assert (dst / "notes.md").read_text(encoding="utf-8") == "plain"
    assert not list(dst.rglob("*-wal")), "sidecars must not be copied alongside a snapshot"
    assert not list(dst.rglob("*-shm"))


def test_snapshot_tree_copies_a_file_that_only_looks_like_a_database(tmp_path: Path) -> None:
    """A non-SQLite file keeps its bytes instead of being fed to sqlite3."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "impostor.sqlite3").write_text("not a database", encoding="utf-8")

    dst = tmp_path / "dst"
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (1, 0)
    assert (dst / "impostor.sqlite3").read_text(encoding="utf-8") == "not a database"

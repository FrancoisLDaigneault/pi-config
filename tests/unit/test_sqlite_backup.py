"""Unit tests for the SQLite-aware snapshot (everything in tmp_path)."""

import shutil
import sqlite3
from pathlib import Path

from pi_config_tools.sqlite_backup import backup_db, is_sqlite, sidecar_parent, snapshot_tree


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


def test_sidecar_parent_names_the_database_each_companion_belongs_to() -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        assert sidecar_parent(Path(f"k.sqlite3{suffix}")) == Path("k.sqlite3")
    assert sidecar_parent(Path("k.sqlite3")) is None
    # A suffix is not a sidecar: this one's parent, `notes`, is nobody.
    assert sidecar_parent(Path("notes-journal")) == Path("notes")


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


def test_snapshot_tree_keeps_a_plain_file_named_like_a_sidecar(tmp_path: Path) -> None:
    """Only a companion of a snapshotted database may be dropped.

    Skipping on the suffix alone deleted `notes-journal` from the backup and
    did not even count it, so the summary reported a success that had lost
    data.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "notes-journal").write_text("field notes", encoding="utf-8")
    (src / "todo-wal").write_text("write a letter", encoding="utf-8")
    (src / "orphan.sqlite3-wal").write_bytes(b"no database of this name here")

    dst = tmp_path / "dst"
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (3, 0), "every file must be copied and counted"
    assert (dst / "notes-journal").read_text(encoding="utf-8") == "field notes"
    assert (dst / "todo-wal").read_text(encoding="utf-8") == "write a letter"
    assert (dst / "orphan.sqlite3-wal").exists(), (
        "a sidecar whose database is absent is an ordinary file, not a companion"
    )


def test_snapshot_tree_drops_a_sidecar_only_beside_its_own_database(tmp_path: Path) -> None:
    """The companion of a real database goes; a same-named stranger stays."""
    src = tmp_path / "src"
    con = _live_wal_db(src / "graph.sqlite3", rows=2)
    try:
        assert (src / "graph.sqlite3-wal").exists(), "the fixture must leave a live WAL"
        (src / "other.sqlite3-wal").write_bytes(b"not a companion of graph.sqlite3")
        dst = tmp_path / "dst"
        files, databases = snapshot_tree(src, dst)
    finally:
        con.close()

    assert (files, databases) == (2, 1)
    assert not (dst / "graph.sqlite3-wal").exists(), "its WAL is folded into the snapshot"
    assert (dst / "other.sqlite3-wal").exists(), "this one belongs to no snapshotted database"
    assert _rows(dst / "graph.sqlite3") == 2


def test_snapshot_tree_copies_a_file_that_only_looks_like_a_database(tmp_path: Path) -> None:
    """A non-SQLite file keeps its bytes instead of being fed to sqlite3."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "impostor.sqlite3").write_text("not a database", encoding="utf-8")

    dst = tmp_path / "dst"
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (1, 0)
    assert (dst / "impostor.sqlite3").read_text(encoding="utf-8") == "not a database"

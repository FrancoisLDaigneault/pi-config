"""Unit tests for the SQLite-aware snapshot (everything in tmp_path)."""

import os
import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from pi_config_tools import sqlite_backup
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


def test_backup_db_gives_up_on_a_database_a_writer_will_not_release(tmp_path: Path) -> None:
    """The connect timeout does not bound backup(); the deadline does.

    Measured before this guard existed: a database held under BEGIN EXCLUSIVE
    kept backup() waiting the full 90 s the lock was held, even though the
    connection carried timeout=5. A stuck writer must fail the section, not
    hang the whole backup.

    The connect timeout is not the smaller of the two here, so it cannot be
    what ends the wait: sqlite would raise OperationalError instead of the
    TimeoutError asserted below. Lowering it under `deadline_s` would shave a
    little time off the run and cost the demonstration.
    """
    src = tmp_path / "held.sqlite3"
    con = sqlite3.connect(src)
    con.execute("CREATE TABLE t (v TEXT)")
    con.executemany("INSERT INTO t VALUES (?)", [(f"row-{i}",) for i in range(2000)])
    con.commit()
    con.close()

    holder = sqlite3.connect(src, isolation_level=None)
    holder.execute("BEGIN EXCLUSIVE")
    dst = tmp_path / "out.sqlite3"
    try:
        with pytest.raises(TimeoutError, match="still locked"):
            backup_db(src, dst, busy_timeout_s=0.05, deadline_s=0.05)
    finally:
        holder.execute("COMMIT")
        holder.close()

    assert dst.stat().st_size == 0, "a snapshot that timed out must hold no partial data"


def test_backup_db_deadline_does_not_disturb_an_unlocked_database(tmp_path: Path) -> None:
    """Batching plus a deadline must not change the ordinary result."""
    src = tmp_path / "free.sqlite3"
    con = _live_wal_db(src, rows=6)
    try:
        dst = tmp_path / "out" / "free.sqlite3"
        backup_db(src, dst, deadline_s=30.0)
    finally:
        con.close()

    assert _rows(dst) == 6


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


def test_snapshot_tree_keeps_the_timestamps_of_the_files_it_copies(tmp_path: Path) -> None:
    """A backup that rewrites every mtime to now cannot answer when a file changed.

    `copy2` over `copy` is the choice that keeps them, and it is one character
    wide: swapping it leaves the content assertions everywhere else untouched,
    so the promise needs an assertion of its own.
    """
    src = tmp_path / "src"
    src.mkdir()
    plain = src / "notes.md"
    plain.write_text("plain", encoding="utf-8")
    long_ago = 1_000_000_000.0
    os.utime(plain, (long_ago, long_ago))

    dst = tmp_path / "dst"
    snapshot_tree(src, dst)

    assert (dst / "notes.md").stat().st_mtime == pytest.approx(long_ago)


def test_snapshot_tree_copies_a_file_that_only_looks_like_a_database(tmp_path: Path) -> None:
    """A non-SQLite file keeps its bytes instead of being fed to sqlite3."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "impostor.sqlite3").write_text("not a database", encoding="utf-8")

    dst = tmp_path / "dst"
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (1, 0)
    assert (dst / "impostor.sqlite3").read_text(encoding="utf-8") == "not a database"


def test_snapshot_tree_snapshots_a_file_that_became_a_database_after_it_was_classified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deciding in the first pass and copying in the second leaves a window.

    A file that is ordinary when the first pass reads it and a live WAL
    database by the time the second pass copies it was copied byte for byte,
    without its -wal. The result answered `ok` to an integrity check and held
    an empty table, which is why the assertion below counts rows: the
    integrity check is exactly what made the loss silent.

    The promotion runs inside the snapshot of the other database, so it lands
    between the two passes without either of them being stubbed.
    """
    src = tmp_path / "src"
    latecomer = src / "aa.data"
    _wal_db(src / "zz.sqlite3", rows=2)
    latecomer.write_text("ordinary when the first pass reads it", encoding="utf-8")

    live: list[sqlite3.Connection] = []
    real_backup_db = sqlite_backup.backup_db

    def snapshot_then_promote_the_latecomer(source: Path, target: Path) -> None:
        real_backup_db(source, target)
        if not live:
            latecomer.unlink()
            live.append(_live_wal_db(latecomer, rows=7))

    monkeypatch.setattr(sqlite_backup, "backup_db", snapshot_then_promote_the_latecomer)
    dst = tmp_path / "dst"
    try:
        files, databases = snapshot_tree(src, dst)
        # Checked before the close: closing checkpoints the WAL and removes it,
        # so a fixture that closes first can never prove the source was live.
        assert (src / "aa.data-wal").exists(), "the source must really be a live database"
    finally:
        for connection in live:
            connection.close()

    con = sqlite3.connect(dst / "aa.data")
    try:
        assert con.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        con.close()
    assert _rows(dst / "aa.data") == 7, "an empty table answers ok to an integrity check too"
    assert not list(dst.rglob("*-wal")), "the WAL is folded in, never copied beside it"
    assert (files, databases) == (2, 2)


def test_snapshot_tree_keeps_a_file_that_stopped_being_a_database_mid_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mirror window: closing one must not open the other.

    A database can be replaced by something else between the moment it is
    recognised and the moment it is snapshotted. Failing there would lose the
    whole backup and skipping it would lose the file, so it is copied for what
    it has become.
    """
    src = tmp_path / "src"
    _wal_db(src / "aa.sqlite3", rows=3)
    victim = src / "aa.sqlite3"

    def replace_it_instead_of_snapshotting_it(source: Path, target: Path) -> None:
        victim.write_text("no longer a database", encoding="utf-8")
        raise sqlite3.DatabaseError("file is not a database")

    monkeypatch.setattr(sqlite_backup, "backup_db", replace_it_instead_of_snapshotting_it)
    dst = tmp_path / "dst"
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (1, 0)
    assert (dst / "aa.sqlite3").read_text(encoding="utf-8") == "no longer a database"


def test_snapshot_tree_still_fails_when_a_real_database_will_not_be_snapshotted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a change of type is tolerated; a genuine failure still propagates."""
    src = tmp_path / "src"
    _wal_db(src / "aa.sqlite3", rows=3)

    def refuse(source: Path, target: Path) -> None:
        raise sqlite3.DatabaseError("disk I/O error")

    monkeypatch.setattr(sqlite_backup, "backup_db", refuse)

    with pytest.raises(sqlite3.DatabaseError, match="disk I/O error"):
        snapshot_tree(src, tmp_path / "dst")


def _promoted_latecomer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, on_second_call: Callable[[], None]
) -> tuple[Path, Path]:
    """A file ordinary in the first pass and a live database in the second.

    `on_second_call` runs when the copying pass reaches it, which is the only
    place the second window can be opened. Returns (src, dst).
    """
    src = tmp_path / "src"
    latecomer = src / "aa.data"
    _wal_db(src / "zz.sqlite3", rows=2)
    latecomer.write_text("ordinary when the first pass reads it", encoding="utf-8")
    live: list[sqlite3.Connection] = []
    real_backup_db = sqlite_backup.backup_db

    def promote_then_hand_over(source: Path, target: Path) -> None:
        if not live:
            real_backup_db(source, target)
            latecomer.unlink()
            live.append(_live_wal_db(latecomer, rows=7))
            return
        live.pop().close()
        on_second_call()

    monkeypatch.setattr(sqlite_backup, "backup_db", promote_then_hand_over)
    return src, tmp_path / "dst"


def test_snapshot_tree_copies_a_latecomer_that_stopped_being_a_database_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mirror window on the copying pass: recognised, then ordinary again.

    Re-reading the header just before the copy closes one race and opens the
    symmetric one. A file that stops being a database between that read and
    the snapshot must still reach the backup, as itself.
    """

    def demote_and_fail() -> None:
        (tmp_path / "src" / "aa.data").write_text("ordinary again", encoding="utf-8")
        raise sqlite3.DatabaseError("file is not a database")

    src, dst = _promoted_latecomer(tmp_path, monkeypatch, demote_and_fail)
    files, databases = snapshot_tree(src, dst)

    assert (files, databases) == (2, 1), "the latecomer is a file again, not a database"
    assert (dst / "aa.data").read_text(encoding="utf-8") == "ordinary again"


def test_snapshot_tree_still_fails_when_a_latecomer_stays_a_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same window, but the file is still a database: the error must surface."""

    def fail_without_demoting() -> None:
        raise sqlite3.DatabaseError("disk I/O error")

    src, dst = _promoted_latecomer(tmp_path, monkeypatch, fail_without_demoting)

    with pytest.raises(sqlite3.DatabaseError, match="disk I/O error"):
        snapshot_tree(src, dst)


def test_snapshot_tree_refuses_a_database_that_landed_as_a_plain_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window no amount of re-reading closes: ordinary, then a database.

    Reading the header again just before the copy narrows the race to two
    adjacent calls, it does not remove it. A file that becomes a live database
    inside that gap is copied byte for byte, without its WAL, and the result
    answers `ok` to an integrity check while holding none of the committed
    rows -- so the assertion below is on the rows, never on the integrity.

    The promotion is injected into `copy2` itself, which is the only place the
    remaining gap can be entered, and nothing of the module under test is
    stubbed.
    """
    src = tmp_path / "src"
    src.mkdir()
    latecomer = src / "aa.data"
    latecomer.write_text("ordinary when the header is read", encoding="utf-8")

    live: list[sqlite3.Connection] = []
    real_copy2 = shutil.copy2

    def promote_then_copy(source: Path, target: Path) -> None:
        if not live:
            latecomer.unlink()
            live.append(_live_wal_db(latecomer, rows=7))
        real_copy2(source, target)

    monkeypatch.setattr(shutil, "copy2", promote_then_copy)
    dst = tmp_path / "dst"
    try:
        with pytest.raises(sqlite3.DatabaseError, match="copied"):
            snapshot_tree(src, dst)
        # Before the close, or the checkpoint would remove the proof.
        assert (src / "aa.data-wal").exists(), "the source must really be a live database"
        assert _rows(latecomer) == 7, "the rows this copy would have dropped"
    finally:
        for connection in live:
            connection.close()

    assert not (dst / "aa.data").exists(), (
        "a database copied as a plain file is removed, not kept as a silent loss"
    )


def test_snapshot_tree_raises_the_original_refusal_when_the_copy_refutes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Demoted, then a database again by the time the plain copy runs.

    That plain copy only happened because a second read said the file had
    stopped being a database. When the copy refutes it, the failure that
    actually happened is the refusal to snapshot, so that is the error which
    has to surface -- not a new one about the copy that followed it.
    """
    live: list[sqlite3.Connection] = []
    real_copy2 = shutil.copy2
    latecomer = tmp_path / "src" / "aa.data"

    def demote_and_refuse() -> None:
        latecomer.write_text("ordinary again", encoding="utf-8")
        raise sqlite3.DatabaseError("disk I/O error")

    def repromote_then_copy(source: Path, target: Path) -> None:
        if not live:
            latecomer.unlink()
            live.append(_live_wal_db(latecomer, rows=5))
        real_copy2(source, target)

    src, dst = _promoted_latecomer(tmp_path, monkeypatch, demote_and_refuse)
    monkeypatch.setattr(shutil, "copy2", repromote_then_copy)
    try:
        with pytest.raises(sqlite3.DatabaseError, match="disk I/O error"):
            snapshot_tree(src, dst)
    finally:
        for connection in live:
            connection.close()

    assert not (dst / "aa.data").exists(), "the database that landed plainly is removed"

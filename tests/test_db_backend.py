import pytest

import openkl.db as db_module
from openkl.db import close_connection, init_db


def test_init_db_creates_core_schema(tmp_path):
    conn = init_db(tmp_path / "ladybug")
    try:
        result = conn.execute("MATCH (m:MemoryNote) RETURN count(m)")
        row = next(iter(result))
        assert row[0] == 0
    finally:
        close_connection()


def test_init_db_raises_when_vector_extension_is_unavailable(tmp_path, monkeypatch):
    class FakeDatabase:
        def __init__(self, path: str):
            self.path = path

        def close(self):
            pass

    class FakeConnection:
        def __init__(self, db: FakeDatabase):
            self.db = db

        def execute(self, stmt: str):
            if stmt in {"INSTALL VECTOR;", "LOAD VECTOR;"}:
                raise RuntimeError("vector extension unavailable")
            return []

        def close(self):
            pass

    monkeypatch.setattr(db_module.graphdb, "Database", FakeDatabase)
    monkeypatch.setattr(db_module.graphdb, "Connection", FakeConnection)

    with pytest.raises(RuntimeError, match="Vector extension is required"):
        init_db(tmp_path / "ladybug")


@pytest.mark.parametrize("existing_ladybug", [False, True])
def test_init_db_blocks_legacy_even_with_existing_ladybug(
    tmp_path, monkeypatch, existing_ladybug
):
    legacy_path = tmp_path / "kuzu"
    ladybug_path = tmp_path / "ladybug"
    legacy_path.mkdir()
    original = legacy_path / "data"
    original.write_bytes(b"legacy data must not be opened by Ladybug")
    if existing_ladybug:
        ladybug_path.write_bytes(b"earlier incomplete Ladybug index")

    monkeypatch.setattr(db_module, "LEGACY_KUZU_DB_PATH", legacy_path)
    monkeypatch.setattr(db_module, "DB_PATH", ladybug_path)

    def fail_open(*args, **kwargs):
        raise AssertionError("must not open a database during migration admission")

    monkeypatch.setattr(db_module.graphdb, "Database", fail_open)
    for path in (None, ladybug_path, legacy_path):
        with pytest.raises(
            db_module.MigrationRequiredError, match="Migration required"
        ):
            init_db(path)
    assert original.read_bytes() == b"legacy data must not be opened by Ladybug"
    assert ladybug_path.exists() == existing_ladybug

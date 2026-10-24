from openkl.db import close_connection, init_db
from openkl.memory import MemoryManager


def test_memory_update_parameterizes_text_and_tags(tmp_path):
    conn = init_db(tmp_path / "ladybug")
    manager = MemoryManager(tmp_path / "ok-home")
    memory_id = "m-20260601-test"

    try:
        conn.execute(
            "CREATE (m:MemoryNote {id: $id, text: $text, ts: $ts, tags: $tags, vec: $vec})",
            {
                "id": memory_id,
                "text": "original",
                "ts": "2026-06-01T00:00:00",
                "tags": ["old"],
                "vec": [0.0] * 384,
            },
        )

        assert manager.update(memory_id, text="O'Reilly note", tags=["review's tag"])

        result = conn.execute(
            "MATCH (m:MemoryNote {id: $id}) RETURN m.text, m.tags",
            {"id": memory_id},
        )
        row = next(iter(result))
        assert row[0] == "O'Reilly note"
        assert row[1] == ["review's tag"]
    finally:
        close_connection()

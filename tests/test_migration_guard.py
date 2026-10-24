"""Exercise upgrade admission against a populated real Kuzu store in an isolated HOME."""

import json
import os
import subprocess
import sys

import pytest

from openkl.db import SCHEMA


def run_python(code, home, *args):
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        input=json.dumps(SCHEMA),
        env={**os.environ, "HOME": str(home), "NO_COLOR": "1", "COLUMNS": "200"},
        text=True,
        capture_output=True,
        timeout=60,
    )


def snapshot(path):
    return {
        str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("existing_ladybug", [False, True])
def test_populated_upgrade_blocks_consumers_and_preserves_legacy(
    tmp_path, existing_ladybug
):
    home = tmp_path / "home"
    root = home / ".ok"
    root.mkdir(parents=True)
    # Kuzu and Ladybug native libraries deliberately run in separate processes.
    legacy_script = """
import json, sys, kuzu
from pathlib import Path
db = kuzu.Database(str(Path.home() / '.ok/kuzu'), buffer_pool_size=64*1024*1024, max_num_threads=2)
conn = kuzu.Connection(db)
schema = json.load(sys.stdin)
if sys.argv[1] == 'create':
    for stmt in schema:
        conn.execute(stmt)
    conn.execute("CREATE (:MemoryNote {id: 'm-legacy', text: 'original memory', ts: '2026-06-01', tags: ['keep']})")
    conn.execute("CREATE (:Topic {id: 'topic-legacy', name: 'legacy'})")
    conn.execute("MATCH (m:MemoryNote), (t:Topic) CREATE (m)-[:HasTopic]->(t)")
    conn.execute("CREATE (:Doc {id: 'doc-legacy', path: 'original.md', sha256: 'abc'})")
    conn.execute("CREATE (:Chunk {id: 'chunk-legacy', text: 'original chunk', span: '0:14'})")
    conn.execute("MATCH (d:Doc), (c:Chunk) CREATE (d)-[:HAS_CHUNK]->(c)")
assert list(conn.execute("MATCH (m:MemoryNote)-[:HasTopic]->(t:Topic) RETURN m.id, m.text, t.id")) == [['m-legacy', 'original memory', 'topic-legacy']]
assert list(conn.execute("MATCH (d:Doc)-[:HAS_CHUNK]->(c:Chunk) RETURN d.id, c.id")) == [['doc-legacy', 'chunk-legacy']]
conn.close()
db.close()
"""
    created = run_python(legacy_script, home, "create")
    assert created.returncode == 0, created.stderr
    memories = root / "memories/by_date/2026-06"
    memories.mkdir(parents=True)
    (memories / "m-legacy.md").write_text("---\nid: m-legacy\n---\noriginal memory\n")
    if existing_ladybug:
        (root / "ladybug").write_bytes(b"earlier incomplete index")
    before = snapshot(root)

    commands = [
        ["doctor"],
        ["mem", "list"],
        ["mem", "search", "original", "--json"],
        ["mem", "update", "m-legacy", "--text", "changed"],
        ["mem", "delete", "m-legacy"],
        ["mem", "add", "new memory"],
        ["store", "list"],
        ["store", "search", "original"],
        ["graph", "cypher", "MATCH (m:MemoryNote) RETURN m.id"],
    ]
    for command in commands:
        result = run_python("from openkl.cli import app; app()", home, *command)
        assert result.returncode == 1, (command, result.stdout, result.stderr)
        assert "Migration required" in result.stdout
        assert "pre-upgrade OpenKL environment" in result.stdout
        assert snapshot(root) == before

    # Library consumers must reject too, before writing files or downloading models.
    result = run_python(
        """
from pathlib import Path
from openkl import MemoryManager, StoreManager
from openkl.db import MigrationRequiredError, init_db
m, s = MemoryManager(), StoreManager()
for operation in (
    init_db, m.list_recent, lambda: m.search('original'),
    lambda: m.update('m-legacy', text='changed'), lambda: m.delete('m-legacy'),
    lambda: m.add('new memory'), s.list_documents, lambda: s.search('original'),
    lambda: s.ingest(Path('unused.md')),
):
    try:
        operation()
    except MigrationRequiredError:
        continue
    raise AssertionError('operation unexpectedly accepted legacy installation')
""",
        home,
    )
    assert result.returncode == 0, result.stderr
    assert snapshot(root) == before
    reopened = run_python(legacy_script, home, "reopen")
    assert reopened.returncode == 0, reopened.stderr
    assert snapshot(root) == before

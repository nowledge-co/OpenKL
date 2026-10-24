"""
Database layer using LadybugDB for graph storage and vector search.
"""

import logging
from pathlib import Path

import ladybug as graphdb

logger = logging.getLogger(__name__)

# Default database path
DB_PATH = Path.home() / ".ok" / "ladybug"
LEGACY_KUZU_DB_PATH = Path.home() / ".ok" / "kuzu"

# LadybugDB schema definitions
SCHEMA = [
    # Memory nodes
    "CREATE NODE TABLE IF NOT EXISTS MemoryNote(id STRING PRIMARY KEY, text STRING, ts STRING, tags STRING[], vec FLOAT[384]);",
    # Grounding Store nodes
    "CREATE NODE TABLE IF NOT EXISTS Doc(id STRING PRIMARY KEY, path STRING, sha256 STRING);",
    "CREATE NODE TABLE IF NOT EXISTS Chunk(id STRING PRIMARY KEY, text STRING, span STRING, vec FLOAT[384]);",
    # Entity and topic nodes
    "CREATE NODE TABLE IF NOT EXISTS Entity(id STRING PRIMARY KEY, name STRING, type STRING);",
    "CREATE NODE TABLE IF NOT EXISTS Topic(id STRING PRIMARY KEY, name STRING);",
    # Relationships
    "CREATE REL TABLE IF NOT EXISTS HAS_CHUNK(FROM Doc TO Chunk);",
    "CREATE REL TABLE IF NOT EXISTS Mentions(FROM Chunk TO Entity);",
    "CREATE REL TABLE IF NOT EXISTS MemMentions(FROM MemoryNote TO Entity);",
    "CREATE REL TABLE IF NOT EXISTS DerivedFrom(FROM MemoryNote TO Chunk);",
    "CREATE REL TABLE IF NOT EXISTS HasTopic(FROM MemoryNote TO Topic);",
]

# Global connection
_connection: graphdb.Connection | None = None
_database: graphdb.Database | None = None


class MigrationRequiredError(RuntimeError):
    """The legacy graph must remain authoritative until explicitly migrated."""


def check_legacy_database(db_path: Path | None = None) -> None:
    """Reject legacy/default graph access before creating or changing any data."""
    target = (DB_PATH if db_path is None else db_path).resolve()
    if LEGACY_KUZU_DB_PATH.exists() and target in {
        DB_PATH.resolve(),
        LEGACY_KUZU_DB_PATH.resolve(),
    }:
        raise MigrationRequiredError(
            f"Migration required: legacy Kuzu database found at {LEGACY_KUZU_DB_PATH}. "
            f"OpenKL cannot automatically migrate it to {DB_PATH}; graph access is "
            "blocked to avoid returning an empty or incomplete index. Keep the entire "
            "~/.ok directory and continue using your pre-upgrade OpenKL environment "
            "(Kuzu backend, revision a4ce8a0730e354d562347843df7dded2de40ae59). "
            "Do not delete or rename the legacy database to bypass this check. "
            "See README: LadybugDB Migration."
        )


def init_db(db_path: Path | None = None) -> graphdb.Connection:
    """Initialize the LadybugDB database with schema."""
    global _connection, _database

    check_legacy_database(db_path)
    if db_path is None:
        db_path = DB_PATH

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database and connection
    close_connection()
    db = graphdb.Database(str(db_path))
    conn = graphdb.Connection(db)

    try:
        # Load a cached extension before attempting a network install.
        try:
            conn.execute("LOAD VECTOR;")
        except Exception:
            try:
                conn.execute("INSTALL VECTOR;")
                conn.execute("LOAD VECTOR;")
            except Exception as e:
                raise RuntimeError("Vector extension is required for OpenKL") from e
        logger.info("Vector extension loaded")

        for stmt in SCHEMA:
            conn.execute(stmt)
            logger.debug(f"Executed schema statement: {stmt[:50]}...")
    except Exception:
        conn.close()
        db.close()
        raise

    _database = db
    _connection = conn
    logger.info(f"Database initialized at {db_path}")
    return conn


def get_connection() -> graphdb.Connection:
    """Get the database connection, initializing if needed."""
    global _connection

    if _connection is None:
        _connection = init_db()

    return _connection


def close_connection() -> None:
    """Close the database connection."""
    global _connection, _database
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("Database connection closed")
    if _database is not None:
        _database.close()
        _database = None

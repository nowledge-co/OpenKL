"""
Database layer using Kùzu DB for graph storage and vector search.
"""

import logging
from pathlib import Path

import kuzu

logger = logging.getLogger(__name__)

# Default database path
DB_PATH = Path.home() / ".ok" / "kuzu"

# Kùzu schema definitions
SCHEMA = [
    # Memory nodes
    "CREATE NODE TABLE MemoryNote(id STRING PRIMARY KEY, text STRING, ts STRING, tags STRING[], vec FLOAT[384]);",
    # Grounding Store nodes
    "CREATE NODE TABLE Doc(id STRING PRIMARY KEY, path STRING, sha256 STRING);",
    "CREATE NODE TABLE Chunk(id STRING PRIMARY KEY, text STRING, span STRING, vec FLOAT[384]);",
    # Entity and topic nodes
    "CREATE NODE TABLE Entity(id STRING PRIMARY KEY, name STRING, type STRING);",
    "CREATE NODE TABLE Topic(id STRING PRIMARY KEY, name STRING);",
    # Relationships
    "CREATE REL TABLE HAS_CHUNK(FROM Doc TO Chunk);",
    "CREATE REL TABLE Mentions(FROM Chunk TO Entity);",
    "CREATE REL TABLE MemMentions(FROM MemoryNote TO Entity);",
    "CREATE REL TABLE DerivedFrom(FROM MemoryNote TO Chunk);",
    "CREATE REL TABLE HasTopic(FROM MemoryNote TO Topic);",
]

# Global connection
_connection: kuzu.Connection | None = None


def init_db(db_path: Path | None = None) -> kuzu.Connection:
    """Initialize the Kùzu database with schema."""
    global _connection

    if db_path is None:
        db_path = DB_PATH

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database and connection
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    # Install and load vector extension
    try:
        conn.execute("INSTALL VECTOR;")
        conn.execute("LOAD VECTOR;")
        logger.info("Vector extension installed and loaded")
    except Exception as e:
        logger.warning(f"Failed to install vector extension: {e}")

    # Create schema
    for stmt in SCHEMA:
        try:
            conn.execute(stmt)
            logger.debug(f"Executed schema statement: {stmt[:50]}...")
        except Exception as e:
            # Ignore "already exists" errors
            if "already exists" not in str(e).lower():
                logger.error(f"Failed to execute schema statement: {stmt}")
                raise

    _connection = conn
    logger.info(f"Database initialized at {db_path}")
    return conn


def get_connection() -> kuzu.Connection:
    """Get the database connection, initializing if needed."""
    global _connection

    if _connection is None:
        _connection = init_db()

    return _connection


def close_connection():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("Database connection closed")

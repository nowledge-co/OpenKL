"""
Vector search utilities leveraging Kùzu's native vector index capabilities.
"""

from typing import Any

from .db import get_connection


def _ensure_vector_extension_loaded(conn, verbose: bool = False):
    """Ensure the vector extension is loaded."""
    try:
        # Try to load the vector extension
        conn.execute("LOAD VECTOR;")
    except Exception as e:
        # If already loaded, ignore the error
        if "already loaded" not in str(e).lower():
            # If not already loaded, try to install and load
            try:
                conn.execute("INSTALL VECTOR;")
                conn.execute("LOAD VECTOR;")
                if verbose:
                    print("✓ Vector extension installed and loaded")
            except Exception as e2:
                raise RuntimeError(f"Failed to load vector extension: {e2}") from e2


def create_vector_indexes(verbose: bool = False):
    """Create vector indexes for memory notes and chunks."""
    conn = get_connection()

    # Ensure vector extension is loaded
    _ensure_vector_extension_loaded(conn, verbose)

    # Create vector index for memory notes
    try:
        conn.execute(
            """
            CALL CREATE_VECTOR_INDEX(
                'MemoryNote',
                'memory_vec_idx',
                'vec',
                metric := 'cosine',
                mu := 30,
                ml := 60,
                pu := 0.05,
                efc := 200,
                cache_embeddings := true
            )
        """
        )
        if verbose:
            print("✓ Memory vector index created")
    except Exception as e:
        if "already exists" in str(e).lower():
            if verbose:
                print("✓ Memory vector index already exists")
        else:
            if verbose:
                print(f"✗ Memory vector index creation failed: {e}")
            raise

    # Create vector index for chunks
    try:
        conn.execute(
            """
            CALL CREATE_VECTOR_INDEX(
                'Chunk',
                'chunk_vec_idx',
                'vec',
                metric := 'cosine',
                mu := 30,
                ml := 60,
                pu := 0.05,
                efc := 200,
                cache_embeddings := true
            )
        """
        )
        if verbose:
            print("✓ Chunk vector index created")
    except Exception as e:
        if "already exists" in str(e).lower():
            if verbose:
                print("✓ Chunk vector index already exists")
        else:
            if verbose:
                print(f"✗ Chunk vector index creation failed: {e}")
            raise


def _ensure_vector_indexes_exist(conn, verbose: bool = False):
    """Ensure vector indexes exist, create them if they don't."""
    try:
        # Check if memory index exists
        result = conn.execute("CALL SHOW_INDEXES() RETURN *")
        indexes = list(result)
        memory_idx_exists = any("memory_vec_idx" in str(idx) for idx in indexes)
        chunk_idx_exists = any("chunk_vec_idx" in str(idx) for idx in indexes)

        if not memory_idx_exists:
            conn.execute(
                """
                CALL CREATE_VECTOR_INDEX(
                    'MemoryNote',
                    'memory_vec_idx',
                    'vec',
                    metric := 'cosine',
                    mu := 30,
                    ml := 60,
                    pu := 0.05,
                    efc := 200,
                    cache_embeddings := true
                )
            """
            )
            if verbose:
                print("✓ Created memory vector index")

        if not chunk_idx_exists:
            conn.execute(
                """
                CALL CREATE_VECTOR_INDEX(
                    'Chunk',
                    'chunk_vec_idx',
                    'vec',
                    metric := 'cosine',
                    mu := 30,
                    ml := 60,
                    pu := 0.05,
                    efc := 200,
                    cache_embeddings := true
                )
            """
            )
            if verbose:
                print("✓ Created chunk vector index")

    except Exception as e:
        if verbose:
            print(f"Warning: Could not ensure vector indexes: {e}")


def search_memory_vectors(
    query_vector: list[float], k: int = 5, verbose: bool = False
) -> list[dict[str, Any]]:
    """Search memory notes using Kùzu's native vector index."""
    conn = get_connection()

    # Ensure vector extension is loaded
    _ensure_vector_extension_loaded(conn, verbose)

    # Ensure vector indexes exist
    _ensure_vector_indexes_exist(conn, verbose)

    # Convert numpy array to list if needed
    if hasattr(query_vector, "tolist"):
        query_vector = query_vector.tolist()

    # Create query with inline vector values
    vector_str = str(query_vector)
    query = f"""
        CALL QUERY_VECTOR_INDEX(
            'MemoryNote',
            'memory_vec_idx',
            {vector_str},
            {k},
            efs := 200
        )
        RETURN node.id as id, node.text as text, node.ts as ts, node.tags as tags, distance
        ORDER BY distance
    """

    result = conn.execute(query)

    results = []
    for row in result:
        memory_id, text, ts, tags, distance = row
        # Convert distance to similarity (1 - distance for cosine similarity)
        similarity = 1.0 - distance
        results.append(
            {
                "id": memory_id,
                "text": text,
                "ts": ts,
                "tags": tags,
                "similarity": similarity,
                "distance": distance,
            }
        )

    return results


def search_chunk_vectors(
    query_vector: list[float], k: int = 5, verbose: bool = False
) -> list[dict[str, Any]]:
    """Search document chunks using Kùzu's native vector index."""
    conn = get_connection()

    # Ensure vector extension is loaded
    _ensure_vector_extension_loaded(conn, verbose)

    # Ensure vector indexes exist
    _ensure_vector_indexes_exist(conn, verbose)

    # Convert numpy array to list if needed
    if hasattr(query_vector, "tolist"):
        query_vector = query_vector.tolist()

    # Create query with inline vector values
    vector_str = str(query_vector)
    query = f"""
        CALL QUERY_VECTOR_INDEX(
            'Chunk',
            'chunk_vec_idx',
            {vector_str},
            {k},
            efs := 200
        )
        WITH node as c, distance
        MATCH (c)-[:HAS_CHUNK]-(d:Doc)
        RETURN c.id as id, c.text as text, d.path as path, d.id as doc_id, distance
        ORDER BY distance
    """

    result = conn.execute(query)

    results = []
    for row in result:
        chunk_id, text, path, doc_id, distance = row
        # Convert distance to similarity (1 - distance for cosine similarity)
        similarity = 1.0 - distance
        results.append(
            {
                "id": chunk_id,
                "text": text,
                "path": path,
                "doc_id": doc_id,
                "similarity": similarity,
                "distance": distance,
            }
        )

    return results


def hybrid_search(
    query_vector: list[float], memory_k: int = 3, chunk_k: int = 3
) -> dict[str, list[dict[str, Any]]]:
    """Perform hybrid search across memory and chunks."""
    memory_results = search_memory_vectors(query_vector, memory_k)
    chunk_results = search_chunk_vectors(query_vector, chunk_k)

    return {"memory": memory_results, "chunks": chunk_results}


def get_vector_stats() -> dict[str, Any]:
    """Get statistics about vector usage in the database."""
    conn = get_connection()

    # Count memory notes with vectors
    memory_result = conn.execute("MATCH (m:MemoryNote) RETURN count(m) as count")
    memory_count = list(memory_result)[0][0]

    # Count chunks with vectors
    chunk_result = conn.execute("MATCH (c:Chunk) RETURN count(c) as count")
    chunk_count = list(chunk_result)[0][0]

    # Get vector dimension
    try:
        vec_result = conn.execute("MATCH (m:MemoryNote) RETURN m.vec LIMIT 1")
        vec_sample = list(vec_result)[0][0]
        vector_dim = len(vec_sample) if vec_sample else 0
    except Exception:
        vector_dim = 0

    # Check if vector indexes exist
    try:
        indexes_result = conn.execute("CALL SHOW_INDEXES() RETURN *")
        indexes = list(indexes_result)
        vector_indexes = [idx for idx in indexes if "vec" in str(idx)]
        index_count = len(vector_indexes)
    except Exception:
        index_count = 0

    return {
        "memory_vectors": memory_count,
        "chunk_vectors": chunk_count,
        "total_vectors": memory_count + chunk_count,
        "vector_dimension": vector_dim,
        "vector_indexes": index_count,
    }


def list_vector_indexes() -> list[dict[str, Any]]:
    """List all vector indexes in the database."""
    conn = get_connection()

    try:
        result = conn.execute("CALL SHOW_INDEXES() RETURN *")
        indexes = []
        for row in result:
            indexes.append(
                {
                    "table_name": row[0],
                    "index_name": row[1],
                    "index_type": row[2],
                    "property_names": row[3],
                    "extension_loaded": row[4],
                    "index_definition": row[5],
                }
            )
        return indexes
    except Exception:
        pass
        return []

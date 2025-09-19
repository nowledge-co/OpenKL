"""
Grounding Store management operations for OpenKL.
"""

import hashlib
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.table import Table

from .db import get_connection
from .parsers import document_parser
from .utils import chunk_text, ensure_dir, get_embedding

console = Console()


class StoreManager:
    """Manages grounding store (external documents) operations."""

    def __init__(self, base_path: Path = Path.home() / ".ok"):
        self.base_path = base_path
        self.store_path = base_path / "store"
        self.sources_path = self.store_path / "sources"
        self.normalized_path = self.store_path / "normalized"

        # Ensure directories exist
        ensure_dir(self.store_path)
        ensure_dir(self.sources_path)
        ensure_dir(self.normalized_path)

    def ingest(self, path: Path, normalize_only: bool = False) -> str:
        """Ingest a document into the grounding store."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Parse document using the enhanced parser
        parse_result = document_parser.parse_document(path)

        if not parse_result["success"]:
            console.print(f"[red]Error parsing {path}:[/red] {parse_result['error']}")
            return ""

        content = parse_result["content"]

        # Generate document ID based on content hash
        doc_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        # Copy to sources if not normalize_only
        if not normalize_only:
            source_path = self.sources_path / path.name
            if not source_path.exists():
                source_path.write_text(content, encoding="utf-8")

        # Create normalized version
        normalized_path = self.normalized_path / f"{doc_id}.ok.md"
        normalized_path.write_text(content, encoding="utf-8")

        # Store in database
        conn = get_connection()

        # Check if doc already exists
        result = conn.execute("MATCH (d:Doc {id: $id}) RETURN d.id", {"id": doc_id})

        if not list(result):
            # Create doc if it doesn't exist
            conn.execute(
                "CREATE (d:Doc {id: $id, path: $path, sha256: $sha256})",
                {
                    "id": doc_id,
                    "path": str(normalized_path),
                    "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                },
            )
        else:
            # Document already exists, check if chunks exist
            chunk_result = conn.execute(
                "MATCH (c:Chunk)-[:HAS_CHUNK]->(d:Doc {id: $id}) RETURN count(c) as chunk_count",
                {"id": doc_id},
            )
            chunk_count = list(chunk_result)[0][0]

            if chunk_count > 0:
                console.print(
                    f"[yellow]Document {doc_id} already exists with {chunk_count} chunks, skipping creation[/yellow]"
                )
                return doc_id
            else:
                console.print(
                    f"[yellow]Document {doc_id} exists but has no chunks, creating chunks[/yellow]"
                )

        # Create chunks
        chunks = chunk_text(content, chunk_size=512, stride=128)
        for i, chunk_content in enumerate(chunks):
            chunk_id = f"{doc_id}#chunk{i:04d}"
            chunk_embedding = get_embedding(chunk_content)

            # Check if chunk already exists
            result = conn.execute(
                "MATCH (c:Chunk {id: $id}) RETURN c.id", {"id": chunk_id}
            )

            if not list(result):
                conn.execute(
                    """
                    CREATE (c:Chunk {id: $id, text: $text, span: $span, vec: $vec})
                    """,
                    {
                        "id": chunk_id,
                        "text": chunk_content,
                        "span": f"chunk_{i}",
                        "vec": chunk_embedding.tolist(),
                    },
                )

                # Create relationship separately
                conn.execute(
                    """
                    MATCH (d:Doc {id: $doc_id}), (c:Chunk {id: $chunk_id})
                    CREATE (d)-[:HAS_CHUNK]->(c)
                    """,
                    {
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                    },
                )

        console.print(
            f"[green]✓[/green] Ingested document: {doc_id} ({len(chunks)} chunks)"
        )
        return doc_id

    def search(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] = None,
        verbose: bool = False,
    ) -> list[dict[str, Any]]:
        """Search grounding store using vector similarity search."""
        from .citations import CitationManager
        from .vector_search import search_chunk_vectors

        if filters is None:
            filters = {}

        # Get query embedding
        query_embedding = get_embedding(query)

        # Use vector similarity search
        results = search_chunk_vectors(query_embedding, k, verbose=verbose)

        # Convert to citation-ready format
        citation_manager = CitationManager()
        citation_results = []

        for result in results:
            # Create transient citation
            transient_cite = citation_manager.create_transient_citation(
                id=result["id"],
                surface="store",
                path=result["path"],
                quote=result["text"],
                loc={"kind": "char", "start": 0, "end": len(result["text"])},
                score=result["similarity"],
            )

            # Clean text for JSON output (replace newlines with spaces)
            clean_text = result["text"].replace("\n", " ").replace("\r", " ")

            citation_results.append(
                {
                    "id": result["id"],
                    "text": clean_text,
                    "path": result["path"],
                    "doc_id": result["doc_id"],
                    "score": result["similarity"],
                    "citation": transient_cite.to_dict(),
                }
            )

        return citation_results

    def list_documents(self) -> list[dict[str, Any]]:
        """List all documents in the store."""
        conn = get_connection()

        result = conn.execute(
            """
            MATCH (d:Doc)
            RETURN d.id as id, d.path as path, d.sha256 as sha256
            ORDER BY d.id
            """
        )

        return [
            {
                "id": row[0],
                "path": row[1],
                "sha256": row[2],
            }
            for row in result
        ]

    def print_results(self, results: list[dict[str, Any]], json_output: bool = False):
        """Print search results."""
        if json_output:
            console.print(JSON.from_data(results))
        else:
            table = Table(title="Store Search Results")
            table.add_column("ID", style="cyan")
            table.add_column("Text", style="white")
            table.add_column("Document", style="green")

            for result in results:
                table.add_row(
                    result["id"],
                    result["text"][:100] + "..."
                    if len(result["text"]) > 100
                    else result["text"],
                    Path(result["path"]).name,
                )

            console.print(table)

    def web(self, url: str, depth: int = 1, max_depth: int = 3, **kwargs) -> str:
        """Ingest web content using Firecrawl (placeholder)."""
        console.print("[yellow]Web ingestion not yet implemented[/yellow]")
        console.print(f"Would ingest: {url} (depth: {depth}, max_depth: {max_depth})")
        console.print(
            "Future implementation will use Firecrawl for web content extraction"
        )
        return ""

    def repo(
        self,
        repo_path: str,
        branch: str = "main",
        include: str = "*.py,*.js,*.md",
        **kwargs,
    ) -> str:
        """Ingest code repository (placeholder)."""
        console.print("[yellow]Repository ingestion not yet implemented[/yellow]")
        console.print(
            f"Would ingest: {repo_path} (branch: {branch}, include: {include})"
        )
        console.print(
            "Future implementation will parse Git repositories and analyze code structure"
        )
        return ""

"""
Memory management operations for OpenKL.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from .db import get_connection
from .utils import ensure_dir, get_embedding

console = Console()


class MemoryManager:
    """Manages memory notes and operations."""

    def __init__(self, base_path: Path = Path.home() / ".ok"):
        self.base_path = base_path
        self.memories_path = base_path / "memories"
        self.by_date_path = self.memories_path / "by_date"
        self.topics_path = self.memories_path / "topics"

        # Ensure directories exist
        ensure_dir(self.memories_path)
        ensure_dir(self.by_date_path)
        ensure_dir(self.topics_path)

    def add(self, text: str, tags: list[str] = None, topics: list[str] = None) -> str:
        """Add a new memory note."""
        if tags is None:
            tags = []
        if topics is None:
            topics = []

        # Generate ID
        timestamp = datetime.now()
        memory_id = f"m-{timestamp.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        # Create frontmatter
        frontmatter = {
            "id": memory_id,
            "ts": timestamp.isoformat(),
            "tags": tags,
            "topics": topics,
        }

        # Create file path
        date_dir = timestamp.strftime("%Y-%m")
        day_dir = self.by_date_path / date_dir
        ensure_dir(day_dir)

        file_path = day_dir / f"{memory_id}.md"

        # Write file
        content = (
            f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n{text}\n"
        )
        file_path.write_text(content, encoding="utf-8")

        # Get embedding
        embedding = get_embedding(text)

        # Store in database (clean text for storage)
        clean_text = text.replace("\n", " ").replace("\r", " ")
        conn = get_connection()
        conn.execute(
            "CREATE (m:MemoryNote {id: $id, text: $text, ts: $ts, tags: $tags, vec: $vec})",
            {
                "id": memory_id,
                "text": clean_text,
                "ts": timestamp.isoformat(),
                "tags": tags,
                "vec": embedding.tolist(),
            },
        )

        # Create topic nodes and relationships
        for topic in topics:
            topic_id = f"topic-{topic.lower().replace(' ', '-')}"
            # Create topic if it doesn't exist
            conn.execute(f"MERGE (t:Topic {{id: '{topic_id}', name: '{topic}'}})")
            # Create relationship
            conn.execute(
                f"MATCH (m:MemoryNote {{id: '{memory_id}'}}), (t:Topic {{id: '{topic_id}'}}) CREATE (m)-[:HasTopic]->(t)"
            )

        # Update topic symlinks
        self._update_topic_symlinks(memory_id, topics)

        console.print(f"[green]✓[/green] Memory added: {memory_id}")
        return memory_id

    def search(
        self, query: str, k: int = 5, verbose: bool = False
    ) -> list[dict[str, Any]]:
        """Search memory notes using vector similarity search."""
        from .citations import CitationManager
        from .vector_search import search_memory_vectors

        # Get query embedding
        query_embedding = get_embedding(query)

        # Use vector similarity search
        results = search_memory_vectors(query_embedding, k, verbose=verbose)

        # Convert to citation-ready format
        citation_manager = CitationManager()
        citation_results = []

        for result in results:
            # Create transient citation
            transient_cite = citation_manager.create_transient_citation(
                id=result["id"],
                surface="memory",
                path=f"memories/by_date/{result['ts'][:7]}/{result['id']}.md",
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
                    "ts": result["ts"],
                    "tags": result["tags"],
                    "score": result["similarity"],
                    "citation": transient_cite.to_dict(),
                }
            )

        return citation_results

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent memory notes."""
        conn = get_connection()

        result = conn.execute(
            """
            MATCH (m:MemoryNote)
            RETURN m.id as id, m.text as text, m.ts as ts, m.tags as tags
            ORDER BY m.ts DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )

        return [
            {
                "id": row[0],
                "text": row[1],
                "ts": row[2],
                "tags": row[3],
            }
            for row in result
        ]

    def update(
        self,
        memory_id: str,
        text: str = None,
        tags: list[str] = None,
        topics: list[str] = None,
    ) -> bool:
        """Update an existing memory note."""
        conn = get_connection()

        # Check if memory exists
        result = conn.execute(f"MATCH (m:MemoryNote {{id: '{memory_id}'}}) RETURN m")
        if not list(result):
            return False

        # Build update query
        updates = []
        if text is not None:
            updates.append(f"m.text = '{text.replace("'", "\\'")}'")
        if tags is not None:
            tags_str = "[" + ", ".join([f"'{tag}'" for tag in tags]) + "]"
            updates.append(f"m.tags = {tags_str}")

        if updates:
            update_query = (
                f"MATCH (m:MemoryNote {{id: '{memory_id}'}}) SET {', '.join(updates)}"
            )
            conn.execute(update_query)

        # Update topics if provided
        if topics is not None:
            # Remove existing topic relationships
            conn.execute(
                f"MATCH (m:MemoryNote {{id: '{memory_id}'}})-[r:HasTopic]->(t) DELETE r"
            )

            # Add new topic relationships
            for topic in topics:
                topic_id = f"topic-{topic.lower().replace(' ', '-')}"
                # Create topic if it doesn't exist
                conn.execute(f"MERGE (t:Topic {{id: '{topic_id}', name: '{topic}'}})")
                # Create relationship
                conn.execute(
                    f"MATCH (m:MemoryNote {{id: '{memory_id}'}}), (t:Topic {{id: '{topic_id}'}}) CREATE (m)-[:HasTopic]->(t)"
                )

        # Update topic symlinks
        self._update_topic_symlinks(memory_id, topics or [])

        # Update the file if text was changed
        if text is not None:
            self._update_memory_file(memory_id, text, tags, topics)

        console.print(f"[green]✓[/green] Memory updated: {memory_id}")
        return True

    def delete(self, memory_id: str) -> bool:
        """Delete a memory note."""
        conn = get_connection()

        # Check if memory exists
        result = conn.execute(f"MATCH (m:MemoryNote {{id: '{memory_id}'}}) RETURN m")
        if not list(result):
            return False

        # Get the date from database before deleting
        result = conn.execute(f"MATCH (m:MemoryNote {{id: '{memory_id}'}}) RETURN m.ts")
        rows = list(result)
        if rows:
            ts = rows[0][0]
            date_part = ts[:7]  # YYYY-MM
            memory_file = self.memories_path / "by_date" / date_part / f"{memory_id}.md"
            if memory_file.exists():
                memory_file.unlink()

        # Delete from database
        conn.execute(f"MATCH (m:MemoryNote {{id: '{memory_id}'}}) DETACH DELETE m")

        # Remove topic symlinks
        self._remove_topic_symlinks(memory_id)

        console.print(f"[green]✓[/green] Memory deleted: {memory_id}")
        return True

    def _update_topic_symlinks(self, memory_id: str, topics: list[str]):
        """Update topic symlinks for a memory note."""
        for topic in topics:
            topic_dir = self.topics_path / topic
            ensure_dir(topic_dir)

            # Create symlink
            # Use the correct date format (YYYY-MM)
            # memory_id format: m-YYYYMMDD-xxxxx
            # Extract YYYY-MM from m-YYYYMMDD-...
            year = memory_id[2:6]  # YYYY
            month = memory_id[6:8]  # MM
            year_month = f"{year}-{month}"
            source_file = self.by_date_path / year_month / f"{memory_id}.md"
            if source_file.exists():
                symlink_path = topic_dir / f"{memory_id}.md"
                if not symlink_path.exists():
                    # Create symlink with absolute path
                    symlink_path.symlink_to(source_file)

    def _remove_topic_symlinks(self, memory_id: str):
        """Remove topic symlinks for a memory note."""
        if not self.topics_path.exists():
            return

        for topic_dir in self.topics_path.iterdir():
            if topic_dir.is_dir():
                symlink_path = topic_dir / f"{memory_id}.md"
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()

    def _update_memory_file(
        self,
        memory_id: str,
        text: str,
        tags: list[str] = None,
        topics: list[str] = None,
    ):
        """Update the memory file on disk."""
        # Get current timestamp
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        # Get current tags and topics from database if not provided
        if tags is None or topics is None:
            conn = get_connection()
            result = conn.execute(
                f"MATCH (m:MemoryNote {{id: '{memory_id}'}}) RETURN m.tags, m.ts"
            )
            rows = list(result)
            if rows:
                current_tags, current_ts = rows[0]
                if tags is None:
                    tags = current_tags
                if topics is None:
                    # Get topics from database
                    topic_result = conn.execute(
                        f"MATCH (m:MemoryNote {{id: '{memory_id}'}})-[:HasTopic]->(t:Topic) RETURN t.name"
                    )
                    topics = [row[0] for row in topic_result]

        # Create frontmatter
        frontmatter = {
            "id": memory_id,
            "tags": tags or [],
            "topics": topics or [],
            "ts": now,
        }

        # Write the file - use the correct date format (YYYY-MM)
        date_part = now[:7]  # YYYY-MM
        memory_file = self.by_date_path / date_part / f"{memory_id}.md"
        memory_file.parent.mkdir(parents=True, exist_ok=True)

        content = "---\n"
        for key, value in frontmatter.items():
            if isinstance(value, list):
                content += f"{key}:\n"
                for item in value:
                    content += f"- {item}\n"
            else:
                content += f"{key}: {value}\n"
        content += f"---\n{text}\n"

        memory_file.write_text(content, encoding="utf-8")

    def print_results(self, results: list[dict[str, Any]], json_output: bool = False):
        """Print search results."""
        if json_output:
            console.print(JSON.from_data(results))
        else:
            table = Table(title="Memory Search Results")
            table.add_column("ID", style="cyan")
            table.add_column("Text", style="white")
            table.add_column("Tags", style="green")
            table.add_column("Timestamp", style="blue")

            for result in results:
                table.add_row(
                    result["id"],
                    result["text"][:100] + "..."
                    if len(result["text"]) > 100
                    else result["text"],
                    ", ".join(result.get("tags", [])),
                    result["ts"][:19] if "ts" in result else "",
                )

            console.print(table)

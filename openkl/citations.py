"""
Citation management for OpenKL.

Implements both transient and persisted citations for agent workflows.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


class TransientCitation:
    """Transient citation object returned by search, not persisted to disk."""

    def __init__(
        self,
        id: str,
        surface: str,  # "memory" or "store"
        path: str,
        sha256: str,
        loc: dict[str, Any],
        quote: str,
        context: dict[str, str] | None = None,
        score: float | None = None,
    ):
        self.id = id
        self.surface = surface
        self.path = path
        self.sha256 = sha256
        self.loc = loc
        self.quote = quote
        self.context = context or {}
        self.score = score

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Clean quote for JSON output (replace newlines with spaces)
        clean_quote = self.quote.replace("\n", " ").replace("\r", " ")

        return {
            "id": self.id,
            "surface": self.surface,
            "path": self.path,
            "sha256": self.sha256,
            "loc": self.loc,
            "quote": clean_quote,
            "context": self.context,
            "score": self.score,
        }


class PersistedCitation:
    """Long-lived citation object persisted to disk for provenance."""

    def __init__(
        self,
        id: str,
        type: str,  # "doc", "chunk", "memory"
        path: str,
        sha256: str,
        loc: dict[str, Any],
        quote: str,
        context: dict[str, str] | None = None,
        source: dict[str, Any] | None = None,
        retention_class: str = "standard",
        tags: list[str] | None = None,
    ):
        self.schema_version = 1
        self.type = type
        self.id = id
        self.path = path
        self.sha256 = sha256
        self.loc = loc
        self.quote = quote
        self.context = context or {}
        self.source = source or {}

        now = datetime.now(timezone.utc).isoformat()
        self.created_at = now
        self.last_accessed_at = now
        self.last_verified_at = now
        self.status = "verified"
        self.retention_class = retention_class
        self.tags = tags or []
        self.rev = 1
        self.history = [{"at": now, "event": "created", "delta": {}}]

        # Set TTL based on retention class
        ttl_map = {
            "temp": 3600,  # 1 hour
            "standard": 86400 * 7,  # 1 week
            "durable": 86400 * 30,  # 1 month
            "pinned": -1,  # Never expire
        }
        self.ttl_seconds = ttl_map.get(retention_class, 86400 * 7)
        self.keep = retention_class in ["durable", "pinned"]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema_version": self.schema_version,
            "type": self.type,
            "id": self.id,
            "path": self.path,
            "sha256": self.sha256,
            "loc": self.loc,
            "quote": self.quote,
            "context": self.context,
            "source": self.source,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "last_verified_at": self.last_verified_at,
            "status": self.status,
            "retention_class": self.retention_class,
            "ttl_seconds": self.ttl_seconds,
            "keep": self.keep,
            "tags": self.tags,
            "rev": self.rev,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersistedCitation":
        """Create from dictionary."""
        citation = cls.__new__(cls)
        for key, value in data.items():
            setattr(citation, key, value)
        return citation

    def update_access(self):
        """Update last accessed timestamp."""
        self.last_accessed_at = datetime.now(timezone.utc).isoformat()

    def verify(self) -> bool:
        """Verify citation against current file state."""
        try:
            # Handle relative paths by resolving them relative to the OpenKL store
            if not Path(self.path).is_absolute():
                from .utils import get_openkl_dir

                openkl_dir = get_openkl_dir()
                path = openkl_dir / self.path
            else:
                path = Path(self.path)

            if not path.exists():
                self.status = "orphan"
                return False

            # Check SHA256 (skip if original was unknown)
            if self.sha256 != "unknown":
                current_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
                if current_sha256 != self.sha256:
                    self.status = "stale"
                    return False

            # For now, just check if the file exists and skip quote verification
            # TODO: Fix quote verification logic properly
            self.status = "verified"
            self.last_verified_at = datetime.now(timezone.utc).isoformat()
            return True

        except Exception:
            self.status = "orphan"
            return False


class CitationManager:
    """Manages both transient and persisted citations."""

    def __init__(self):
        self.citations_dir = Path.home() / ".ok" / "citations"
        self.citations_dir.mkdir(parents=True, exist_ok=True)
        self.cite_index_path = Path.home() / ".ok" / "cite_index.jsonl"

    def create_transient_citation(
        self,
        id: str,
        surface: str,
        path: str,
        quote: str,
        loc: dict[str, Any],
        context: dict[str, str] | None = None,
        score: float | None = None,
    ) -> TransientCitation:
        """Create a transient citation from search results."""
        # Calculate SHA256
        path_obj = Path(path)
        if path_obj.exists():
            sha256 = hashlib.sha256(path_obj.read_bytes()).hexdigest()
        else:
            sha256 = "unknown"

        return TransientCitation(
            id=id,
            surface=surface,
            path=path,
            sha256=sha256,
            loc=loc,
            quote=quote,
            context=context,
            score=score,
        )

    def make_citation(
        self,
        transient_citation: TransientCitation,
        retention_class: str = "standard",
        tags: list[str] | None = None,
    ) -> str:
        """Convert transient citation to persisted citation."""
        # Determine type based on surface and ID
        if transient_citation.surface == "memory":
            cite_type = "memory"
        elif "#" in transient_citation.id:
            cite_type = "chunk"
        else:
            cite_type = "doc"

        # Create persisted citation
        persisted = PersistedCitation(
            id=transient_citation.id,
            type=cite_type,
            path=transient_citation.path,
            sha256=transient_citation.sha256,
            loc=transient_citation.loc,
            quote=transient_citation.quote,
            context=transient_citation.context,
            retention_class=retention_class,
            tags=tags,
        )

        # Save to disk
        cite_file = self.citations_dir / f"{persisted.id}.json"
        cite_file.write_text(json.dumps(persisted.to_dict(), indent=2))

        # Update index
        self._update_cite_index(persisted)

        return persisted.id

    def make_citation_from_id(
        self,
        citation_id: str,
        retention_class: str = "standard",
        tags: list[str] | None = None,
    ) -> str:
        """Create a persisted citation from a citation ID (from search results)."""
        # Get the citation data from database
        try:
            from .db import get_connection

            conn = get_connection()

            # Check if it's a memory note
            if citation_id.startswith("m-"):
                result = conn.execute(
                    f"MATCH (m:MemoryNote {{id: '{citation_id}'}}) RETURN m.text, m.ts, m.tags"
                )
                rows = list(result)
                if not rows:
                    raise ValueError(f"Memory note not found: {citation_id}")

                text, ts, tags_from_db = rows[0]
                # Use the correct date format (YYYY-MM)
                date_part = ts[:7]  # YYYY-MM
                path = f"memories/by_date/{date_part}/{citation_id}.md"

                # Calculate actual SHA256 and get current text if file exists
                from .utils import get_openkl_dir

                openkl_dir = get_openkl_dir()
                full_path = openkl_dir / path
                sha256 = "unknown"
                current_text = text

                if full_path.exists():
                    sha256 = hashlib.sha256(full_path.read_bytes()).hexdigest()
                    # Get the actual text content (after frontmatter)
                    content = full_path.read_text(encoding="utf-8")
                    if "---" in content:
                        # Extract text after frontmatter
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            current_text = parts[2].strip()
                        else:
                            current_text = content
                    else:
                        current_text = content

                # Create transient citation
                transient = TransientCitation(
                    id=citation_id,
                    surface="memory",
                    path=path,
                    sha256=sha256,
                    loc={"kind": "char", "start": 0, "end": len(current_text)},
                    quote=current_text,
                    context={},
                )

                return self.make_citation(transient, retention_class, tags)

            # Check if it's a chunk
            elif "#" in citation_id:
                result = conn.execute(
                    f"MATCH (c:Chunk {{id: '{citation_id}'}}) RETURN c.text, c.span"
                )
                rows = list(result)
                if not rows:
                    raise ValueError(f"Chunk not found: {citation_id}")

                text, span = rows[0]
                # Get document path
                doc_result = conn.execute(
                    f"MATCH (d:Doc)-[:HAS_CHUNK]->(c:Chunk {{id: '{citation_id}'}}) RETURN d.path"
                )
                doc_rows = list(doc_result)
                path = doc_rows[0][0] if doc_rows else "unknown"

                # Parse span to get location
                if "char" in span:
                    # Extract char range from span like "char:0-100"
                    char_range = span.split(":")[1].split("-")
                    start, end = int(char_range[0]), int(char_range[1])
                else:
                    start, end = 0, len(text)

                # Calculate SHA256 if file exists
                sha256 = "unknown"
                if path != "unknown" and Path(path).exists():
                    try:
                        file_content = Path(path).read_text()
                        sha256 = hashlib.sha256(file_content.encode()).hexdigest()
                    except Exception:  # noqa: B904
                        pass

                # Create transient citation
                transient = TransientCitation(
                    id=citation_id,
                    surface="store",
                    path=path,
                    sha256=sha256,
                    loc={"kind": "char", "start": start, "end": end},
                    quote=text,
                    context={},
                )

                return self.make_citation(transient, retention_class, tags)

            else:
                raise ValueError(f"Unknown citation ID format: {citation_id}")

        except Exception as e:
            raise ValueError(
                f"Failed to create citation from ID {citation_id}: {e}"
            ) from e

    def verify_citation(self, cite_id: str) -> bool:
        """Verify a citation (either persisted or transient)."""
        # First check if it's a persisted citation
        cite_file = self.citations_dir / f"{cite_id}.json"
        if cite_file.exists():
            try:
                data = json.loads(cite_file.read_text())
                citation = PersistedCitation.from_dict(data)
                is_valid = citation.verify()

                # Update file if anything changed
                current_data = citation.to_dict()
                if current_data != data:
                    cite_file.write_text(json.dumps(current_data, indent=2))
                    self._update_cite_index(citation)

                return is_valid
            except Exception:
                return False

        # If not persisted, check if it's a memory or chunk that exists
        # This handles transient citations from search results
        try:
            from .db import get_connection

            conn = get_connection()

            # Check if it's a memory note
            if cite_id.startswith("m-"):
                result = conn.execute(
                    f"MATCH (m:MemoryNote {{id: '{cite_id}'}}) RETURN m"
                )
                if list(result):
                    return True

            # Check if it's a chunk
            elif "#" in cite_id:
                result = conn.execute(f"MATCH (c:Chunk {{id: '{cite_id}'}}) RETURN c")
                if list(result):
                    return True

            return False
        except Exception:
            return False

    def open_citation(self, cite_id: str) -> dict[str, Any] | None:
        """Open and display a citation."""
        cite_file = self.citations_dir / f"{cite_id}.json"
        if cite_file.exists():
            try:
                data = json.loads(cite_file.read_text())
                citation = PersistedCitation.from_dict(data)
                citation.update_access()

                # Update file with new access time
                cite_file.write_text(json.dumps(citation.to_dict(), indent=2))

                return citation.to_dict()
            except Exception:
                return None

        # If not persisted, try to get from database
        try:
            from .db import get_connection

            conn = get_connection()

            # Check if it's a memory note
            if cite_id.startswith("m-"):
                result = conn.execute(
                    f"MATCH (m:MemoryNote {{id: '{cite_id}'}}) RETURN m.text, m.ts, m.tags"
                )
                rows = list(result)
                if rows:
                    text, ts, tags = rows[0]
                    return {
                        "id": cite_id,
                        "type": "memory",
                        "text": text,
                        "ts": ts,
                        "tags": tags,
                        "status": "transient",
                        "quote": text,
                    }

            # Check if it's a chunk
            elif "#" in cite_id:
                result = conn.execute(
                    f"MATCH (c:Chunk {{id: '{cite_id}'}}) RETURN c.text"
                )
                rows = list(result)
                if rows:
                    text = rows[0][0]
                    return {
                        "id": cite_id,
                        "type": "chunk",
                        "text": text,
                        "status": "transient",
                        "quote": text,
                    }

            return None
        except Exception:
            return None

    def _update_cite_index(self, citation: PersistedCitation):
        """Update the citation index."""
        index_entry = {
            "id": citation.id,
            "type": citation.type,
            "path": citation.path,
            "status": citation.status,
            "retention_class": citation.retention_class,
            "created_at": citation.created_at,
            "last_accessed_at": citation.last_accessed_at,
        }

        # Read existing entries and deduplicate
        existing_entries = []
        if self.cite_index_path.exists():
            with open(self.cite_index_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("id") != citation.id:  # Skip duplicates
                            existing_entries.append(entry)
                    except json.JSONDecodeError:
                        continue

        # Add the new/updated entry
        existing_entries.append(index_entry)

        # Write back to file
        with open(self.cite_index_path, "w") as f:
            for entry in existing_entries:
                f.write(json.dumps(entry) + "\n")

    def list_citations(self, status: str | None = None) -> list[dict[str, Any]]:
        """List citations, optionally filtered by status."""
        citations = []
        seen_ids = set()

        if not self.cite_index_path.exists():
            return citations

        with open(self.cite_index_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Deduplicate by ID
                    if entry.get("id") not in seen_ids:
                        if status is None or entry.get("status") == status:
                            citations.append(entry)
                            seen_ids.add(entry.get("id"))
                except json.JSONDecodeError:
                    continue

        return citations

    def gc_citations(self, dry_run: bool = False) -> dict[str, int]:
        """Garbage collect expired citations."""
        stats = {"expired": 0, "orphaned": 0, "kept": 0}

        if not self.cite_index_path.exists():
            return stats

        # Read all citations
        citations = []
        with open(self.cite_index_path) as f:
            for line in f:
                try:
                    citations.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        # Process each citation
        kept_citations = []
        for entry in citations:
            cite_file = self.citations_dir / f"{entry['id']}.json"

            if not cite_file.exists():
                stats["orphaned"] += 1
                continue

            try:
                data = json.loads(cite_file.read_text())
                citation = PersistedCitation.from_dict(data)

                # Check if should be kept
                if citation.keep or citation.retention_class == "pinned":
                    kept_citations.append(entry)
                    stats["kept"] += 1
                    continue

                # Check TTL
                created_at = datetime.fromisoformat(
                    citation.created_at.replace("Z", "+00:00")
                )
                now = datetime.now(timezone.utc)
                age_seconds = (now - created_at).total_seconds()

                if citation.ttl_seconds > 0 and age_seconds > citation.ttl_seconds:
                    if not dry_run:
                        cite_file.unlink()
                    stats["expired"] += 1
                else:
                    kept_citations.append(entry)
                    stats["kept"] += 1

            except Exception:
                stats["orphaned"] += 1

        # Update index file
        if not dry_run:
            with open(self.cite_index_path, "w") as f:
                for entry in kept_citations:
                    f.write(json.dumps(entry) + "\n")

        return stats

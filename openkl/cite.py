"""
Citation management system for OpenKL.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()


class CitationManager:
    """Manages citations for reproducible references."""

    def __init__(self, base_path: Path = Path.home() / ".ok"):
        self.base_path = base_path
        self.citations_path = base_path / "citations"

        # Ensure directory exists
        self.citations_path.mkdir(parents=True, exist_ok=True)

    def make(
        self, path: Path, lines: str | None = None, chars: str | None = None
    ) -> str:
        """Create a citation for a specific location in a file."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Read file content
        content = path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Parse location specification
        if lines:
            start_line, end_line = self._parse_lines(lines)
            start_char, end_char = self._get_char_range_from_lines(
                content, start_line, end_line
            )
        elif chars:
            start_char, end_char = self._parse_chars(chars)
        else:
            # Default to entire file
            start_char, end_char = 0, len(content)

        # Extract quote
        quote = content[start_char:end_char]

        # Get context
        context_pre = content[max(0, start_char - 100) : start_char]
        context_post = content[end_char : min(len(content), end_char + 100)]

        # Generate citation ID
        cite_id = hashlib.sha256(
            f"{path}:{start_char}:{end_char}".encode()
        ).hexdigest()[:16]

        # Create citation object
        citation = {
            "type": "doc",
            "id": cite_id,
            "path": str(path),
            "sha256": content_hash,
            "loc": {
                "kind": "char",
                "start": start_char,
                "end": end_char,
            },
            "quote": quote,
            "context": {
                "pre": context_pre,
                "post": context_post,
            },
            "source": {
                "url": f"file://{path.absolute()}",
            },
            "created_at": datetime.now().isoformat(),
        }

        # Save citation
        cite_file = self.citations_path / f"{cite_id}.json"
        cite_file.write_text(json.dumps(citation, indent=2), encoding="utf-8")

        console.print(f"[green]✓[/green] Citation created: {cite_id}")
        console.print(f"URI: okcite://{cite_id}")

        return cite_id

    def verify(self, cite_id: str) -> bool:
        """Verify a citation is still valid."""
        cite_file = self.citations_path / f"{cite_id}.json"

        if not cite_file.exists():
            console.print(f"[red]✗[/red] Citation not found: {cite_id}")
            return False

        # Load citation
        citation = json.loads(cite_file.read_text(encoding="utf-8"))
        path = Path(citation["path"])

        if not path.exists():
            console.print(f"[red]✗[/red] File not found: {path}")
            return False

        # Check file hash
        current_content = path.read_text(encoding="utf-8")
        current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()

        if current_hash != citation["sha256"]:
            console.print("[red]✗[/red] File has changed since citation was created")
            return False

        # Check quote still matches
        loc = citation["loc"]
        current_quote = current_content[loc["start"] : loc["end"]]

        if current_quote != citation["quote"]:
            console.print("[red]✗[/red] Quote no longer matches at specified location")
            return False

        console.print(f"[green]✓[/green] Citation verified: {cite_id}")
        return True

    def open(self, cite_id: str) -> bool:
        """Open and display a citation with context."""
        cite_file = self.citations_path / f"{cite_id}.json"

        if not cite_file.exists():
            console.print(f"[red]✗[/red] Citation not found: {cite_id}")
            return False

        # Load citation
        citation = json.loads(cite_file.read_text(encoding="utf-8"))
        path = Path(citation["path"])

        if not path.exists():
            console.print(f"[red]✗[/red] File not found: {path}")
            return False

        # Read file and extract section
        loc = citation["loc"]

        console.print(f"\n[bold]Citation:[/bold] {cite_id}")
        console.print(f"[bold]File:[/bold] {path}")
        console.print(f"[bold]Location:[/bold] chars {loc['start']}-{loc['end']}")
        console.print("\n[bold]Quote:[/bold]")
        console.print(">>>> (begin cite) <<<<")
        console.print(citation["quote"])
        console.print(">>>> (end cite) <<<<")

        return True

    def _parse_lines(self, lines: str) -> tuple[int, int]:
        """Parse line specification like '100-120'."""
        if "-" in lines:
            start, end = lines.split("-", 1)
            return int(start) - 1, int(end)  # Convert to 0-based indexing
        else:
            line = int(lines) - 1
            return line, line + 1

    def _parse_chars(self, chars: str) -> tuple[int, int]:
        """Parse character specification like '1000-2000'."""
        if "-" in chars:
            start, end = chars.split("-", 1)
            return int(start), int(end)
        else:
            pos = int(chars)
            return pos, pos + 1

    def _get_char_range_from_lines(
        self, content: str, start_line: int, end_line: int
    ) -> tuple[int, int]:
        """Convert line numbers to character positions."""
        lines = content.split("\n")

        start_char = 0
        for i in range(start_line):
            start_char += len(lines[i]) + 1  # +1 for newline

        end_char = start_char
        for i in range(start_line, min(end_line, len(lines))):
            end_char += len(lines[i]) + 1  # +1 for newline

        return start_char, end_char

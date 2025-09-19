"""
Document parsing utilities using kreuzberg and other tools.
"""

import hashlib
from pathlib import Path
from typing import Any

try:
    import kreuzberg
except ImportError:
    kreuzberg = None
try:
    from arxiv import Search
except ImportError:
    Search = None


class DocumentParser:
    """Enhanced document parser using kreuzberg and other tools."""

    def __init__(self):
        pass

    def parse_pdf(self, pdf_path: Path) -> str:
        """Parse PDF file to markdown using kreuzberg."""
        try:
            # Use kreuzberg to parse PDF
            result = kreuzberg.extract_file_sync(str(pdf_path))
            # Check what attributes are available
            if hasattr(result, "text"):
                return result.text
            elif hasattr(result, "content"):
                return result.content
            else:
                # Try to get text from the result
                return str(result)
        except Exception:
            # Fallback to basic text extraction
            return self._fallback_pdf_parse(pdf_path)

    def parse_html(self, html_path: Path) -> str:
        """Parse HTML file to markdown."""
        try:
            import html2text

            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()

            # Convert to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False

            markdown_content = h.handle(html_content)
            return markdown_content
        except Exception:
            return html_path.read_text(encoding="utf-8")

    def parse_markdown(self, md_path: Path) -> str:
        """Parse markdown file (already in markdown format)."""
        return md_path.read_text(encoding="utf-8")

    def parse_txt(self, txt_path: Path) -> str:
        """Parse plain text file."""
        return txt_path.read_text(encoding="utf-8")

    def _fallback_pdf_parse(self, pdf_path: Path) -> str:
        """Fallback PDF parsing method."""
        try:
            import PyPDF2

            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception:
            return f"[PDF content from {pdf_path.name} - parsing failed]"

    def parse_document(self, file_path: Path) -> dict[str, Any]:
        """Parse any supported document type."""
        file_extension = file_path.suffix.lower()

        try:
            if file_extension == ".pdf":
                content = self.parse_pdf(file_path)
            elif file_extension in [".html", ".htm"]:
                content = self.parse_html(file_path)
            elif file_extension == ".md":
                content = self.parse_markdown(file_path)
            elif file_extension == ".txt":
                content = self.parse_txt(file_path)
            else:
                # Try to read as text
                content = file_path.read_text(encoding="utf-8")

            return {
                "success": True,
                "content": content,
                "file_type": file_extension,
                "file_size": file_path.stat().st_size,
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "file_type": file_extension}


class ArXivIngester:
    """Ingest papers from ArXiv."""

    def __init__(self, parser: DocumentParser):
        self.parser = parser

    def download_paper(self, arxiv_id: str, output_dir: Path) -> dict[str, Any]:
        """Download and parse an ArXiv paper."""
        try:
            # Search for the paper
            search = Search(id_list=[arxiv_id])
            results = list(search.results())

            if not results:
                return {"success": False, "error": f"Paper {arxiv_id} not found"}

            paper = results[0]

            # Download PDF
            pdf_path = output_dir / f"{arxiv_id}.pdf"
            paper.download_pdf(str(output_dir), filename=f"{arxiv_id}.pdf")

            # Parse the PDF
            parse_result = self.parser.parse_document(pdf_path)

            if not parse_result["success"]:
                return parse_result

            # Create metadata
            metadata = {
                "arxiv_id": arxiv_id,
                "title": paper.title,
                "authors": [author.name for author in paper.authors],
                "published": paper.published.isoformat() if paper.published else None,
                "summary": paper.summary,
                "pdf_url": paper.pdf_url,
                "categories": paper.categories,
                "doi": paper.doi,
                "journal_ref": paper.journal_ref,
            }

            # Create markdown content
            markdown_content = self._create_paper_markdown(
                metadata, parse_result["content"]
            )

            # Save markdown version
            md_path = output_dir / f"{arxiv_id}.md"
            md_path.write_text(markdown_content, encoding="utf-8")

            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "title": paper.title,
                "pdf_path": str(pdf_path),
                "md_path": str(md_path),
                "metadata": metadata,
                "content_length": len(parse_result["content"]),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "arxiv_id": arxiv_id}

    def _create_paper_markdown(self, metadata: dict[str, Any], content: str) -> str:
        """Create markdown representation of the paper."""
        md_lines = [
            f"# {metadata['title']}",
            "",
            f"**ArXiv ID:** {metadata['arxiv_id']}",
            f"**Authors:** {', '.join(metadata['authors'])}",
            f"**Published:** {metadata['published'] or 'Unknown'}",
            f"**Categories:** {', '.join(metadata['categories'])}",
            "",
            "## Abstract",
            "",
            metadata["summary"],
            "",
            "## Full Text",
            "",
            content,
        ]

        if metadata.get("doi"):
            md_lines.extend(
                [
                    "",
                    "## References",
                    "",
                    f"**DOI:** {metadata['doi']}",
                    f"**PDF URL:** {metadata['pdf_url']}",
                ]
            )

        return "\n".join(md_lines)


# Global instances
document_parser = DocumentParser()
arxiv_ingester = ArXivIngester(document_parser)

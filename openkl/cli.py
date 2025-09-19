"""
Command-line interface for OpenKL.
"""

from pathlib import Path

import typer
from rich.console import Console

from . import init_db
from .citations import CitationManager
from .distill import DistillationManager
from .graph import GraphManager
from .memory import MemoryManager
from .parsers import arxiv_ingester
from .store import StoreManager

app = typer.Typer(name="ok", help="Open Knowledge Layer CLI")
console = Console()

# Initialize managers
memory_manager = MemoryManager()
store_manager = StoreManager()
graph_manager = GraphManager()
citation_manager = CitationManager()
distill_manager = DistillationManager()


@app.command()
def doctor(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """Check environment and dependencies."""
    console.print("[bold]OpenKL Environment Check[/bold]")

    # Check Python packages
    try:
        import kuzu  # noqa: F401

        console.print("[green]✓[/green] Kùzu DB available")
    except ImportError:
        console.print("[red]✗[/red] Kùzu DB not found")

    try:
        import fastembed  # noqa: F401

        console.print("[green]✓[/green] FastEmbed available")
    except ImportError:
        console.print("[red]✗[/red] FastEmbed not found")

    # Check ripgrep
    import shutil

    if shutil.which("rg"):
        console.print("[green]✓[/green] ripgrep (rg) available")
    else:
        console.print(
            "[yellow]⚠[/yellow] ripgrep (rg) not found - will use Python fallback"
        )

    # Check jq
    if shutil.which("jq"):
        console.print("[green]✓[/green] jq available")
    else:
        console.print("[yellow]⚠[/yellow] jq not found - installing...")
        try:
            import subprocess

            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            subprocess.run(
                ["apt-get", "install", "-y", "jq"], check=True, capture_output=True
            )
            console.print("[green]✓[/green] jq installed successfully")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to install jq: {e}")
            console.print("[yellow]⚠[/yellow] Some examples may not work without jq")

    # Initialize database
    try:
        init_db()
        console.print("[green]✓[/green] Database initialized")
    except Exception as e:
        console.print(f"[red]✗[/red] Database initialization failed: {e}")

    console.print("\n[bold green]Environment check complete![/bold green]")


# Memory commands
mem_app = typer.Typer(help="Memory operations")
app.add_typer(mem_app, name="mem")


@mem_app.command("add")
def mem_add(
    text: str = typer.Argument(..., help="Memory text to add"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    topics: str | None = typer.Option(None, help="Comma-separated topics"),
):
    """Add a new memory note."""
    tag_list = tags.split(",") if tags else []
    topic_list = topics.split(",") if topics else []

    memory_id = memory_manager.add(text, tag_list, topic_list)
    console.print(f"Memory added with ID: {memory_id}")


@mem_app.command("search")
def mem_search(
    query: str = typer.Argument(..., help="Search query"),
    k: int = typer.Option(5, help="Number of results"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """Search memory notes."""
    results = memory_manager.search(query, k=k, verbose=verbose)
    memory_manager.print_results(results, json_output=json)


@mem_app.command("update")
def mem_update(
    memory_id: str = typer.Argument(..., help="Memory ID to update"),
    text: str = typer.Option(None, help="New text content"),
    tags: str = typer.Option(None, help="Comma-separated tags"),
    topics: str = typer.Option(None, help="Comma-separated topics"),
):
    """Update an existing memory note."""
    tag_list = tags.split(",") if tags else None
    topic_list = topics.split(",") if topics else None

    success = memory_manager.update(
        memory_id, text=text, tags=tag_list, topics=topic_list
    )
    if not success:
        console.print(f"[red]✗[/red] Memory not found: {memory_id}")


@mem_app.command("delete")
def mem_delete(
    memory_id: str = typer.Argument(..., help="Memory ID to delete"),
):
    """Delete a memory note."""
    success = memory_manager.delete(memory_id)
    if not success:
        console.print(f"[red]✗[/red] Memory not found: {memory_id}")


@mem_app.command("list")
def mem_list(
    limit: int = typer.Option(10, help="Number of recent memories to show"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List recent memory notes."""
    results = memory_manager.list_recent(limit=limit)
    memory_manager.print_results(results, json_output=json)


# Store commands
store_app = typer.Typer(help="Grounding Store operations")
app.add_typer(store_app, name="store")


@store_app.command("ingest")
def store_ingest(
    path: Path = typer.Argument(..., help="Path to file or directory to ingest"),
    normalize_only: bool = typer.Option(
        False, help="Only normalize, don't copy to sources"
    ),
):
    """Ingest documents into the grounding store."""
    if path.is_file():
        doc_id = store_manager.ingest(path, normalize_only=normalize_only)
        if doc_id:
            console.print(f"Document ingested with ID: {doc_id}")
    else:
        console.print("[yellow]Directory ingestion not implemented yet[/yellow]")


@store_app.command("arxiv")
def store_arxiv(
    arxiv_id: str = typer.Argument(..., help="ArXiv ID (e.g., 1706.03762)"),
    output_dir: Path | None = typer.Option(
        None, help="Output directory for downloaded files"
    ),
):
    """Download and ingest an ArXiv paper."""
    if output_dir is None:
        output_dir = Path.home() / ".ok" / "papers"

    output_dir.mkdir(parents=True, exist_ok=True)

    result = arxiv_ingester.download_paper(arxiv_id, output_dir)

    if result["success"]:
        console.print(f"[green]✓[/green] Paper downloaded: {result['title']}")
        console.print(f"PDF: {result['pdf_path']}")
        console.print(f"Markdown: {result['md_path']}")

        # Also ingest the markdown version
        md_path = Path(result["md_path"])
        doc_id = store_manager.ingest(md_path, normalize_only=True)
        if doc_id:
            console.print(f"Document ingested with ID: {doc_id}")
    else:
        console.print(f"[red]✗[/red] Failed to download paper: {result['error']}")


@store_app.command("search")
def store_search(
    query: str = typer.Argument(..., help="Search query"),
    k: int = typer.Option(5, help="Number of results"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """Search the grounding store."""
    results = store_manager.search(query, k=k, verbose=verbose)
    store_manager.print_results(results, json_output=json)


@store_app.command("list")
def store_list(
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all documents in the store."""
    results = store_manager.list_documents()
    if json:
        console.print_json(data=results)
    else:
        from rich.table import Table

        table = Table(title="Documents in Store")
        table.add_column("ID", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("SHA256", style="green")

        for doc in results:
            table.add_row(doc["id"], Path(doc["path"]).name, doc["sha256"][:16] + "...")

        console.print(table)


@store_app.command("web")
def store_web(
    url: str = typer.Argument(..., help="URL to ingest"),
    depth: int = typer.Option(1, "--depth", help="Crawl depth"),
    max_depth: int = typer.Option(3, "--max-depth", help="Maximum crawl depth"),
):
    """Ingest web content using Firecrawl (placeholder)."""
    store_manager.web(url, depth=depth, max_depth=max_depth)


@store_app.command("repo")
def store_repo(
    repo_path: str = typer.Argument(..., help="Repository path or URL"),
    branch: str = typer.Option("main", "--branch", help="Git branch to analyze"),
    include: str = typer.Option(
        "*.py,*.js,*.md", "--include", help="File patterns to include"
    ),
):
    """Ingest code repository (placeholder)."""
    store_manager.repo(repo_path, branch=branch, include=include)


# Graph commands
graph_app = typer.Typer(help="Graph operations")
app.add_typer(graph_app, name="graph")


@graph_app.command("cypher")
def graph_cypher(
    query: str = typer.Argument(..., help="Cypher query to execute"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Execute a Cypher query on the knowledge graph."""
    results = graph_manager.run_cypher(query)
    graph_manager.print_results(results, json_output=json)


@graph_app.command("stats")
def graph_stats():
    """Show graph statistics."""
    stats = graph_manager.get_entity_stats()
    console.print("[bold]Graph Statistics[/bold]")
    for key, value in stats.items():
        console.print(f"{key}: {value}")


@graph_app.command("vector-stats")
def vector_stats():
    """Show vector statistics."""
    from .vector_search import get_vector_stats

    stats = get_vector_stats()
    console.print("[bold]Vector Statistics[/bold]")
    for key, value in stats.items():
        console.print(f"{key}: {value}")


@graph_app.command("list-indexes")
def list_indexes():
    """List all vector indexes."""
    from .vector_search import list_vector_indexes

    indexes = list_vector_indexes()
    if not indexes:
        console.print("[yellow]No indexes found[/yellow]")
        return

    console.print("[bold]Vector Indexes[/bold]")
    for idx in indexes:
        console.print(f"Table: {idx['table_name']}")
        console.print(f"  Index: {idx['index_name']}")
        console.print(f"  Type: {idx['index_type']}")
        console.print(f"  Properties: {idx['property_names']}")
        console.print(f"  Extension Loaded: {idx['extension_loaded']}")
        console.print("")


# Search command
@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    surface: str = typer.Option("both", help="Search surface: mem, store, or both"),
    k: int = typer.Option(10, help="Number of results"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """Hybrid search across memory and store."""
    all_results = []

    if surface in ["mem", "both"]:
        mem_results = memory_manager.search(
            query, k=k // 2 if surface == "both" else k, verbose=verbose
        )
        for result in mem_results:
            result["source"] = "memory"
        all_results.extend(mem_results)

    if surface in ["store", "both"]:
        store_results = store_manager.search(
            query, k=k // 2 if surface == "both" else k, verbose=verbose
        )
        for result in store_results:
            result["source"] = "store"
        all_results.extend(store_results)

    # Print results
    if json:
        console.print_json(data=all_results)
    else:
        from rich.table import Table

        table = Table(title=f"Search Results for: {query}")
        table.add_column("Source", style="cyan")
        table.add_column("ID", style="green")
        table.add_column("Text", style="white")

        for result in all_results:
            table.add_row(
                result.get("source", "unknown"),
                result["id"],
                result["text"][:100] + "..."
                if len(result["text"]) > 100
                else result["text"],
            )

        console.print(table)


# Citation commands
cite_app = typer.Typer(help="Citation operations")
app.add_typer(cite_app, name="cite")


@cite_app.command("make")
def cite_make(
    citation_id: str = typer.Argument(..., help="Citation ID from search results"),
    retention_class: str = typer.Option(
        "standard", help="Retention class: temp, standard, durable, pinned"
    ),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
):
    """Create a persisted citation from a transient citation ID."""
    try:
        tag_list = tags.split(",") if tags else None
        persisted_id = citation_manager.make_citation_from_id(
            citation_id, retention_class=retention_class, tags=tag_list
        )
        console.print(f"[green]✓[/green] Citation created: {persisted_id}")
        console.print(f"Retention class: {retention_class}")
        if tags:
            console.print(f"Tags: {tags}")
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create citation: {e}")


@cite_app.command("verify")
def cite_verify(
    cite_id: str = typer.Argument(..., help="Citation ID to verify"),
):
    """Verify a citation against current file state."""
    is_valid = citation_manager.verify_citation(cite_id)
    if is_valid:
        console.print(f"[green]✓[/green] Citation verified: {cite_id}")
    else:
        console.print(f"[red]✗[/red] Citation invalid or not found: {cite_id}")


@cite_app.command("open")
def cite_open(
    cite_id: str = typer.Argument(..., help="Citation ID to open"),
):
    """Open and display a citation."""
    citation_data = citation_manager.open_citation(cite_id)
    if citation_data:
        console.print(f"[bold]Citation:[/bold] {cite_id}")
        if "path" in citation_data:
            console.print(f"[bold]File:[/bold] {citation_data['path']}")
        console.print(f"[bold]Type:[/bold] {citation_data.get('type', 'unknown')}")
        console.print(f"[bold]Status:[/bold] {citation_data['status']}")
        if "ts" in citation_data:
            console.print(f"[bold]Timestamp:[/bold] {citation_data['ts']}")
        console.print("[bold]Quote:[/bold]")
        console.print(">>>> (begin cite) <<<<")
        console.print(citation_data["quote"])
        console.print(">>>> (end cite) <<<<")
    else:
        console.print(f"[red]✗[/red] Citation not found: {cite_id}")


@cite_app.command("list")
def cite_list(
    status: str | None = typer.Option(None, help="Filter by status"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List citations."""
    citations = citation_manager.list_citations(status=status)
    if not citations:
        console.print("[yellow]No citations found[/yellow]")
        return

    if json:
        console.print_json(data=citations)
        return

    from rich.table import Table

    table = Table(title="Citations")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Path", style="blue")
    table.add_column("Created", style="dim")

    for cite in citations:
        table.add_row(
            cite["id"],
            cite["type"],
            cite["status"],
            cite["path"],
            cite["created_at"][:10],
        )

    console.print(table)


@cite_app.command("gc")
def cite_gc(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
):
    """Garbage collect expired citations."""
    stats = citation_manager.gc_citations(dry_run=dry_run)

    console.print("[bold]Citation Garbage Collection[/bold]")
    console.print(f"Expired: {stats['expired']}")
    console.print(f"Orphaned: {stats['orphaned']}")
    console.print(f"Kept: {stats['kept']}")

    if dry_run:
        console.print("[yellow]Dry run - no changes made[/yellow]")


# Index command
@app.command()
def index():
    """Build or update indexes."""
    console.print("[yellow]Indexing not implemented yet[/yellow]")


# Sync command
@app.command()
def sync():
    """Sync file system with database."""
    console.print("[yellow]Sync not implemented yet[/yellow]")


# Distillation commands
distill_app = typer.Typer(help="Memory distillation operations")
app.add_typer(distill_app, name="distill")


@distill_app.command("create")
def distill_create(
    content: str = typer.Argument(..., help="Distilled content from agent"),
    source_citations: str = typer.Argument(
        ..., help="Comma-separated source citation IDs"
    ),
    tags: str = typer.Option(None, "--tags", help="Comma-separated tags"),
    topics: str = typer.Option(None, "--topics", help="Comma-separated topics"),
):
    """Create memory from agent-distilled content."""
    cite_list = [cid.strip() for cid in source_citations.split(",")]
    tag_list = tags.split(",") if tags else None
    topic_list = topics.split(",") if topics else None

    memory_id = distill_manager.create_memory_from_distillation(
        content, cite_list, tags=tag_list, topics=topic_list
    )

    if memory_id:
        console.print(f"[green]✓[/green] Memory created: {memory_id}")
    else:
        console.print("[red]✗[/red] Memory creation failed")


@distill_app.command("get-prompt")
def distill_get_prompt(
    prompt_type: str = typer.Argument(..., help="Type of distillation prompt"),
):
    """Get a distillation prompt template for agents to use."""
    distill_manager.get_prompt_template(prompt_type)


@distill_app.command("prompts")
def distill_prompts():
    """List available distillation prompts."""
    distill_manager.list_distillation_prompts()


if __name__ == "__main__":
    app()

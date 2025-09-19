# Open Knowledge Layer (OpenKL)

A local-first, open-source knowledge and memory layer for AI agents. OpenKL provides a unified protocol and implementation that allows any agent (human, SWE agent, or other AI systems) to easily access and interact with knowledge for a single user.

> [!NOTE]
>
> This project is still under the very early stage of development, please expect its full shape in Alpha version soon!

## Features

- **Memory Management**: Distilled insights, facts, and user-provided notes with temporal organization
- **Grounding Store**: External knowledge corpus (docs, media, logs, transcripts) with automatic chunking
- **Knowledge Graph**: Structured entities and relationships with provenance using Kùzu DB
- **Citations**: Reproducible, verifiable, portable references with both transient and persisted modes
- **Vector Search**: Native HNSW vector indexes with FastEmbed for semantic similarity
- **Hybrid Search**: Cross-surface search across memory and grounding store
- **Memory Distillation**: Standardized prompts for agent-driven knowledge synthesis
- **File System Integration**: Grep-friendly, pipe-first CLI design
- **Agent Integration**: Citation-ready JSON output for programmatic access

## Quick Start

### Installation

OpenKL uses `uv` for fast Python package management. Install `uv` first:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install OpenKL
uv sync

# Or install globally with uvx
# uvx openkl
```

### Usage

```bash
# Initialize database
ok doctor

# Add memory
ok mem add "API rate limit is 100 req/min"

# Search memory
ok mem search "rate limit"

# Ingest documents
ok store ingest ./docs

# Ingest ArXiv papers
ok store arxiv 1706.03762

# Search everything
ok search "retry budget algorithm"

# View graph statistics
ok graph stats

# Run Cypher queries
ok graph cypher "MATCH (m:MemoryNote) RETURN count(m) as memory_count"

# Create persisted citation from search result
ok cite make m-20250919-4b5d3cb1 --retention-class durable --tags "reliability,patterns"

# Verify citation
ok cite verify m-20250919-4b5d3cb1

# Open citation
ok cite open m-20250919-4b5d3cb1

# List citations
ok cite list

# Update memory
ok mem update m-20250919-4b5d3cb1 --text "Updated text" --tags "new,tags"

# Delete memory
ok mem delete m-20250919-4b5d3cb1

# List vector indexes
ok graph list-indexes

# Get distillation prompt for agents
ok distill get-prompt memory-synthesis

# Create memory from agent-distilled content
ok distill create "Your distilled content" "citation1,citation2" --tags "insight,distilled"
```

### Agent Integration

For AI agents and automated workflows, see [examples/agents.md](examples/agents.md) for detailed integration patterns and examples.

For the technical design specification, see [rfcs/0000-openkl-design.md](rfcs/0000-openkl-design.md).

### Examples

See [examples/DEMO.md](examples/DEMO.md) for quick examples demonstrating OpenKL's core capabilities.

### Development

```bash
# Install in development mode
uv sync --dev

# Run tests
uv run pytest

# Run the CLI
uv run ok --help
```

## Architecture

OpenKL uses a file-based approach with an embedded Kùzu graph database:

- **Files**: Canonical content (grep-friendly)
- **Graph**: Derived structure (fast retrieval)
- **Citations**: Stable provenance and verification

## License

Apache License 2.0

## Inspired by and Related Projects

- [Manus Context Engineering Blog Post](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [SemTools](https://github.com/run-llama/semtools)
- [Agent Client Protocol](https://agentclientprotocol.com/)
- [Fusion GraphRAG Blog Post](https://siwei.io/fusion-graphrag-2025/)
- [Nowledge Mem](https://mem.nowledge.co/)

# Open Knowledge Layer (OpenKL) - RFC

**number:** 0000
**Author:** wey-gu
**Status:** Draft
**Date:** 2025-09-19

## 1. Motivation

Modern AI agents need both:

- **Grounding** — retrieval from external documents, transcripts, logs, etc.
- **Memory** — distilled, persistent insights from conversations, grounding resources, or user input

Current frameworks (Zep, SemTools) solve parts of this but often:

- Are multi-tenant/cloud-centric, not single-user/local
- Emphasize either memory or retrieval, not both
- Lack a consistent protocol bridging file-based workflows and graph/index backends

OpenKL aims to unify these needs:

- Local-first, open-source, transparent
- Minimal, composable tools (SemTools-style)
- File system ergonomics + Graph/Vector performance
- Auditable, portable Citations for provenance

## 2. Core Concepts

- **Memory**: User/agent-authored notes. Temporal (by date) and topical (tags → symlinks)
- **Grounding Store**: Ingested external material. Canonical original (sources/), normalized text (normalized/*.ok.md). Supports ArXiv papers, web content (via Firecrawl), code repositories, and various document formats
- **Knowledge Graph**: Derived structure (entities, relationships, chunk nodes). Links back to Memory + Grounding via citations

## 3. File System Contract

### 3.1 Directory Structure

```bash
openkl/
├─ store/                         # Grounding Store (authored files + normalized text)
│  ├─ sources/                    # originals: pdf, html, txt, srt, md, …
│  │  └─ <any tree you like>
│  └─ normalized/                 # one *.ok.md per source (text-only, stable)
│     └─ <mirror of sources>/*.ok.md
├─ memories/
│  ├─ by_date/YYYY-MM/DD/<id>.md  # authored notes (frontmatter+body)
│  └─ topics/<slug>/...           # optional views/symlinks
├─ graph/                         # derived/exports (optional, not persisted by default)
│  ├─ snapshots/*.graphml
│  ├─ entities.csv
│  └─ relations.csv
├─ citations/                     # stable cite objects (JSONL)
│  └─ <id>.json
└─ .ok/                           # internal
   ├─ kuzu/                       # embedded Graph DB
   ├─ cache/
   ├─ mapping.jsonl               # docID → current path mapping
   └─ config.yml
```

### 3.2 File System Principles

- **Files are canonical** for authored content (grep-friendly)
- **Graph/index is derived** (fast retrieval, not persisted by default)
- **Renames/reorg safe**: docID = content hash; only add/delete matter
- **Hierarchical independence**: Graph never depends on file tree structure
- **Mapping file**: `.ok/mapping.jsonl` tracks docID → current path for renames
- **Vector indexes**: Created automatically when needed, not manually managed

### 3.3 Memory Organization

- **Canonical view**: `memories/by_date/YYYY-MM/DD/<id>.md`
- **Virtual views**: `topics/<slug>/` symlinks regenerated from tags
- **Frontmatter example**:

```yaml
---
id: m-20250918-abcd
ts: "2025-09-18T10:22:11Z"
tags: [throttling, scaling]
topics: [llm, infra]
---
Insight text…
```

## 4. Graph + Index Design

**Engine**: [Kùzu DB](https://docs.kuzudb.com/) (embedded, Cypher, HNSW vectors, FT index)

**Schema (conceptual)**:

- MemoryNote(id, text, ts, tags, vec)
- Doc(id, path, sha256)
- Chunk(id, text, span, vec)
- Entity(id, name, type)
- Relations:
  - (Doc)-[:HAS_CHUNK]->(Chunk)
  - (Chunk)-[:MENTIONS]->(Entity)
  - (Memory)-[:MENTIONS]->(Entity)
  - (Memory)-[:DERIVED_FROM]->(Doc|Chunk)
  - (Memory)-[:HAS_TOPIC]->(Topic)

**Chunking**: only in DB (default 512 tokens, stride 128). Optional dump for debugging.

## 5. Citations System

### 5.1 Motivation

Citations provide:

- **Stable provenance**: What document + where exactly
- **Verifiability**: Can re-open and see exact text in context
- **Portability**: Ship answer + cites to another machine, still verify
- **Agent-safe anchoring**: Agent can request cite, verify, then include in answer

### 5.2 ID Scheme

- **Doc ID**: `sha256(bytes of normalized .ok.md)[:16]` (content-addressed, rename-safe)
- **Chunk ID**: `docID#tok[start]-[end]` (token span) or `docID#char[start]-[end]`
- **Memory ID**: `m-<time>-<random4>` (or content-hash for full determinism)

### 5.3 Cite Object

```json
{
  "type": "doc|chunk|memory",
  "id": "8e1f9a62#tok1200-1450",
  "path": "store/normalized/papers/xyz.ok.md",
  "sha256": "…",
  "loc": {"kind":"char","start":7231,"end":7615},
  "quote": "Exact snippet…",
  "context": {"pre":"…", "post":"…"},
  "source": {"url":"file:///…/xyz.pdf","page":12},
  "created_at": "2025-09-18T11:03:22Z"
}
```

### 5.4 Citation CLI

- `ok cite make <path> --lines 100-120` → writes cite JSON, prints URI
- `ok cite verify <id|uri>` → true/false + diagnostics
- `ok cite open <id>` → open file and highlight span (TTY-friendly markers)

## 6. Tool Surface

### 6.1 Human CLI (pipe-first, all support --json)

- `ok mem add/search/update/delete`
- `ok store ingest/arxiv/web/repo/search`
- `ok search "query"` → cross-surface hybrid, returns Cite objects
- `ok graph cypher` (RO default)
- `ok cite make|verify|open|list`
- `ok distill` → extract insights from grounding store to memory
- `ok index`, `ok sync`, `ok doctor`

### 6.2 Agent Tools

- `mem_search`, `mem_add`
- `store_search`, `store_ingest`, `store_cite`
- `graph_cypher`
- `fs_list`, `fs_read`
- `sh_grep` (safe wrapper, rg if present, Python fallback otherwise)

**Agent Integration Guide**: See [examples/agents.md](examples/agents.md) for detailed integration patterns, examples, and best practices for AI agents using OpenKL.

## 7. Memory Distillation

### 7.1 Concept

Memory distillation is the process of extracting insights from grounding store content and creating structured memories. This bridges the gap between raw documents and actionable knowledge.

### 7.2 Distillation Workflow

```bash
# 1. Search grounding store for relevant content
ok search "distributed systems patterns" --json

# 2. Create citations for important findings
ok cite make <chunk_id> --retention-class durable --tags "patterns,reliability"

# 3. Get distillation prompt for agent
ok distill get-prompt identify-patterns

# 4. Agent uses prompt with LLM to distill content
# (Agent evaluates prompt and generates distilled content)

# 5. Create memory from agent-distilled content
ok distill create "Distilled patterns and principles" <citation_ids> \
  --tags "patterns,reliability"

# 6. Verify and refine
ok mem search "distributed patterns" --json
```

### 7.3 Distillation Prompts

Standard prompts for different types of distillation:

- **`extract-facts`**: Extract factual information and key details
- **`identify-patterns`**: Find recurring patterns and principles
- **`summarize-insights`**: Create high-level summaries
- **`extract-relationships`**: Identify connections between concepts
- **`extract-entities`**: Find important entities and their properties
- **`memory-synthesis`**: Synthesize into actionable memory entry

### 7.4 Graph Edge Creation

Distillation automatically creates graph relationships:

- `(MemoryNote)-[:DerivedFrom]->(Chunk)` - Links memory to source chunks
- `(MemoryNote)-[:Mentions]->(Entity)` - Links memory to extracted entities
- `(MemoryNote)-[:HasTopic]->(Topic)` - Links memory to topics

## 8. Retrieval Behavior

- **Hybrid search**: vector + FT, score fusion, dedupe per doc
- **Output**: Cite objects only (verifiable, portable)
- **Re-ranking**: promote diversity, limit per doc
- **Agentic pipeline** (standardized):
  1. `sh_grep` (fast filter)
  2. `store_search` (semantic)
  3. `graph_cypher` (entity hops)
  4. `cite` for provenance
  5. `distill` for insight extraction
  6. `mem_add` for persistent storage

## 8. Safety & Ergonomics

- **rg preferred** for grep (fast, JSON output); `ok doctor` checks + bundles binary; fallback to Python
- **All writes explicit** (`mem_add`, `store_ingest`)
- **Logs for reproducibility** (`--tee .ok/ops.log`)
- **Agent tools capped** (k, bytes, timeouts)
- **Privacy**: everything local; no cloud by default

## 9. Implementation Details

### 9.1 Python Package Layout

```bash
openkl/
├─ __init__.py
├─ cli.py             # Typer CLI entrypoint
├─ db.py              # GraphDB wrapper + schema
├─ memory.py          # memory operations
├─ store.py           # grounding store ops
├─ graph.py           # Cypher helpers
├─ citations.py       # citation management (transient + persisted)
├─ vector_search.py   # vector search with GraphDB HNSW indexes
├─ parsers.py         # document parsing (PDF, HTML, Markdown)
├─ utils.py           # utilities (embedding, chunking)
├─ api.py             # API server (placeholder)
└─ server.py          # HTTP server (placeholder)
```

**Install with uv**:

```bash
uv sync
# Or install globally
uvx openkl
```

### 9.2 GraphDB Schema DDL

```sql
-- Memory (384-dimensional vectors with FastEmbed)
CREATE NODE TABLE MemoryNote(id STRING PRIMARY KEY, text STRING, ts STRING, tags STRING[], vec FLOAT[384]);

-- Grounding Docs
CREATE NODE TABLE Doc(id STRING PRIMARY KEY, path STRING, sha256 STRING);
CREATE NODE TABLE Chunk(id STRING PRIMARY KEY, text STRING, span STRING, vec FLOAT[384]);

-- Entities
CREATE NODE TABLE Entity(id STRING PRIMARY KEY, name STRING, type STRING);
CREATE NODE TABLE Topic(id STRING PRIMARY KEY, name STRING);

-- Relations
CREATE REL TABLE HAS_CHUNK(FROM Doc TO Chunk);
CREATE REL TABLE Mentions(FROM Chunk TO Entity);
CREATE REL TABLE MemMentions(FROM MemoryNote TO Entity);
CREATE REL TABLE DerivedFrom(FROM MemoryNote TO Chunk);
CREATE REL TABLE HasTopic(FROM MemoryNote TO Topic);

-- Vector Indexes (HNSW)
CALL CREATE_VECTOR_INDEX('MemoryNote', 'memory_vec_idx', 'vec', metric := 'cosine');
CALL CREATE_VECTOR_INDEX('Chunk', 'chunk_vec_idx', 'vec', metric := 'cosine');
```

### 9.3 Current Implementation Status

**✅ Implemented:**

- Memory management with temporal organization (add, search, update, delete)
- Document ingestion with automatic chunking (PDF, HTML, Markdown via Kreuzberg)
- Vector search using GraphDB HNSW indexes with FastEmbed (384-dimensional)
- Citation system (transient and persisted modes with verification)
- Hybrid search across memory and grounding store
- Graph statistics and Cypher query interface
- ArXiv paper ingestion and processing
- Topic symlink regeneration and management
- Pre-commit hooks with ruff formatting and linting
- Memory update and delete operations
- Citation creation from search results (via `ok cite make`)
- Memory distillation from search results and citations (via `ok distill`)
- Graph relationship creation for distilled memories

**🔄 In Progress:**

- Entity extraction and relationship linking
- API server implementation (basic structure exists)

**📋 Planned:**

- Web content ingestion via [Firecrawl](https://github.com/firecrawl/firecrawl) (placeholder commands exist)
- Code repository ingestion and analysis (placeholder commands exist)
- Memory consolidation/forgetting
- Export commands
- Knowledge graph visualization and exploration

## 10. Command Examples

### 10.1 Ingest + Search

```bash
# Ingest documents
ok store ingest docs/whitepapers

# Ingest ArXiv papers
ok store arxiv 1706.03762

# Search across all knowledge
ok search "transformer architecture"
```

### 10.2 Search → Create Citations → Verify

```bash
# Search for information
ok search "transformer architecture" --json

# Create citations for important findings
ok search "transformer architecture" --json | jq -r '.[].id' | head -3 | \
  xargs -I {} ok cite make {} --retention-class durable --tags "transformer,architecture"

# Verify citations
ok cite list
```

### 10.3 Memory + Graph Exploration

```bash
# Search memory for insights
ok mem search "transformer" --json

# Explore graph relationships
ok graph cypher "MATCH (m:MemoryNote)-[:HasTopic]->(t:Topic) RETURN t.name, count(m) as memories"

# Find related concepts
ok graph cypher "MATCH (m:MemoryNote)-[:HasTopic]->(t:Topic {name: 'nlp'}) RETURN m.id, m.text"
```

### 10.4 Memory Management

```bash
# Add insights to memory
ok mem add "Transformers use self-attention for parallel processing" \
  --tags "transformer,attention,architecture" --topics "nlp,deep-learning"

# Update existing memory
ok mem update m-20250919-abc123 --text "Updated insight" --tags "new,tags"

# Delete outdated information
ok mem delete m-20250919-abc123
```

### 10.5 Knowledge Graph Exploration

```bash
# Find entities mentioned in transformer-related memories
ok graph cypher "MATCH (m:MemoryNote)-[:HasTopic]->(t:Topic {name: 'transformer'})-[:Mentions]->(e:Entity) RETURN e.name, e.type, count(m) as mentions ORDER BY mentions DESC"

# Discover relationships between concepts
ok graph cypher "MATCH (m1:MemoryNote)-[:Mentions]->(e:Entity)<-[:Mentions]-(m2:MemoryNote) WHERE m1.id <> m2.id RETURN e.name, collect(DISTINCT m1.id) as memories"

# Find related documents through entity connections
ok graph cypher "MATCH (m:MemoryNote)-[:DerivedFrom]->(c:Chunk)-[:HAS_CHUNK]->(d:Doc) WHERE m.text CONTAINS 'attention' RETURN d.path, c.text LIMIT 5"

# Explore topic hierarchies and relationships
ok graph cypher "MATCH (t1:Topic)-[:RelatedTo*1..2]->(t2:Topic) RETURN t1.name, t2.name, length(path) AS distance"
```

### 10.6 Future Grounding Store Commands

```bash
# Web content ingestion (planned)
ok store web "https://example.com/article" --depth 2
ok store web "https://docs.example.com" --recursive --max-depth 3

# Code repository ingestion (planned)
ok store repo "https://github.com/user/repo" --branch main
ok store repo "/local/path/to/repo" --include "*.py,*.js,*.md"

# Multi-format document parsing
ok store ingest "document.pdf" --format pdf
ok store ingest "presentation.pptx" --format pptx
ok store ingest "spreadsheet.xlsx" --format xlsx
```

## 11. Roadmap

### MVP (Next 1-2 Days)

- Scaffold Python package + CLI (`ok`)
- Implement:
  - `mem add/search`
  - `store ingest/search` (txt, md, pdf)
  - `graph cypher` (RO)
  - `cite make/verify/open`
  - `index`, `sync`, `doctor`
  - GraphDB schema + embeddings (sentence-transformers)

### Next

- Entity extraction + graph linking
- Topic symlink regeneration
- API server exposing tools
- Export commands
- MCP prompts and tools based Protocol
- Memory consolidation/forgetting (later)

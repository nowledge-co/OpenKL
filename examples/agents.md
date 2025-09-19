# OpenKL Agent Integration Guide

This guide helps AI agents integrate with OpenKL for knowledge management, memory distillation, and **reproducible reasoning through citations**.

## 🎯 **Core Principles for AI Agents**

### **When to Use Each Component**

1. **Grounding Store** → Raw external material (papers, docs, transcripts)
2. **Memory** → Your distilled insights and facts
3. **Citations** → Provenance tracking for reproducible reasoning
4. **Distillation** → Knowledge synthesis with full traceability

### **Agent Decision Tree**

```text
New Information Encountered
├── Is it raw external material? → Grounding Store
├── Is it a distilled insight? → Memory + Citations
├── Need to synthesize knowledge? → Distillation + Citations
└── Need to reference sources? → Use Citations
```

---

## 🚀 **Essential Commands**

### **Search & Discovery**

```bash
# Search memories
uv run ok mem search "transformer attention" --json

# Search grounding store
uv run ok store search "BERT bidirectional" --json

# Hybrid search across both
uv run ok search "transformer architecture" --json
```

### **Citation Management**

```bash
# Create citations for key findings
# Using jq (preferred):
uv run ok search "transformer" --json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer"

# Fallback without jq:
# uv run ok search "transformer" --json | grep -o '"id": "[^"]*"' | head -3 | cut -d'"' -f4 | \
#   xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer"

# List all citations
ok cite list

# Open a citation to see full context
ok cite open 43411d2b03b695e1#chunk0036

# Verify citation integrity
ok cite verify 43411d2b03b695e1#chunk0036
```

### **Memory Management**

```bash
# Add memory with topics and tags
uv run ok mem add "Your insight here" --tags "tag1,tag2" --topics "topic1,topic2"

# Update existing memory
uv run ok mem update m-20250919-abc123 "Updated content"

# Search memories
uv run ok mem search "query" --json

# Delete memory
uv run ok mem delete m-20250919-abc123
```

### **Distillation Workflow**

```bash
# 1. Search for relevant information
uv run ok search "transformer architecture" --json > search_results.json

# 2. Create citations for key findings
cat search_results.json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer,architecture"

# 3. Get distillation prompt for your LLM
uv run ok distill get-prompt memory-synthesis

# 4. Use the prompt with your LLM to distill content
# (Your agent evaluates the prompt and generates distilled content)

# 5. Create memory from distilled content
uv run ok distill create "Your distilled content here" \
  "43411d2b03b695e1#chunk0036,831514a53d5ea432#chunk0000" \
  --tags "transformer,architecture" --topics "nlp"

# 6. Verify the memory was created with proper relationships
uv run ok mem search "transformer" --json

# 7. Check graph relationships (use specific relationship queries)
uv run ok graph cypher "MATCH (m:MemoryNote)-[r:DerivedFrom]->(c:Chunk) RETURN m.id, c.id" --json
```

---

## 🔧 **Advanced Agent Workflows**

### **1. REPRODUCIBLE REASONING: Citations in Action**

```bash
# Search for information and create citations
uv run ok search "transformer architecture" --json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer,architecture"

# Generate response with proper citations
echo "Based on my knowledge base, here are the key insights about transformer architecture:

$(cat search_results.json | jq -r '.[] | "- \(.text) (okcite://\(.id))"')

These insights are grounded in the following sources:
$(ok cite list | grep "transformer\|architecture" | head -3)"
```

**Example Output:**

```
Based on my knowledge base, here are the key insights about transformer architecture:

- Transformers use self-attention mechanisms for parallel processing... (okcite://m-20250919-283cb946)
- Self-attention allows the model to attend to different positions... (okcite://m-20250919-375470ed)
- Multi-head attention allows the model to jointly attend... (okcite://m-20250919-d88b47ef)

These insights are grounded in the following sources:
│ 43411d2b03b695e1#ch… │ chunk  │ verified │ /home/ubuntu/.ok/st… │ 2025-09-19 │
│ 831514a53d5ea432#ch… │ chunk  │ verified │ /home/ubuntu/.ok/st… │ 2025-09-19 │
```

**Why This Matters:** Citations provide **reproducible provenance** - every claim can be traced back to its source!

### **2. CONTEXT WINDOW MANAGEMENT: Smart Citation Usage**

```bash
# Instead of including entire documents, agents can cite specific sections
echo "Based on my knowledge base, here are the key insights about transformer architecture:

$(uv run ok search "transformer" --json | jq -r '.[] | "- \(.text) (okcite://\(.id))"')

These insights are grounded in the following sources:
$(ok cite list | grep "transformer\|architecture" | head -3)"
```

**Why This Matters:** Citations enable **context-efficient responses** - agents can reference sources without overwhelming the context window!

### **3. KNOWLEDGE SYNTHESIS: Agent-Driven Distillation**

```bash
# 1. Search for relevant information
uv run ok search "transformer architecture" --json > search_results.json

# 2. Create citations for key findings
cat search_results.json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer,architecture"

# 3. Get distillation prompt for your LLM
uv run ok distill get-prompt memory-synthesis

# 4. Use the prompt with your LLM to distill content
# (Your agent evaluates the prompt and generates distilled content)

# 5. Create memory from distilled content
uv run ok distill create "Your distilled content here" \
  "43411d2b03b695e1#chunk0036,831514a53d5ea432#chunk0000" \
  --tags "transformer,architecture" --topics "nlp"

# 6. Verify the memory was created with proper relationships
uv run ok mem search "transformer" --json

# 7. Check graph relationships (use specific relationship queries)
uv run ok graph cypher "MATCH (m:MemoryNote)-[r:DerivedFrom]->(c:Chunk) RETURN m.id, c.id" --json
```

**Example Output:**

```json
[
  {"m.id": "m-20250919-9416162a", "c.id": "43411d2b03b695e1#chunk0036"},
  {"m.id": "m-20250919-9416162a", "c.id": "831514a53d5ea432#chunk0000"}
]
```

**Why This Matters:** Distillation creates **knowledge graphs** - agents can synthesize insights and OpenKL automatically tracks provenance!

### **4. GRAPH-AWARE RETRIEVAL: Connection Discovery**

```bash
# "What memories are connected through shared topics?"
uv run ok graph cypher "MATCH (m1:MemoryNote)-[:HasTopic]->(t:Topic)<-[:HasTopic]-(m2:MemoryNote) WHERE m1.id <> m2.id RETURN t.name, collect(m1.id) as memories" --json | \
  jq -r '.[] | "Topic: \(."t.name")\nMemories: \(."memories" | join(", "))\n---"'

# "What documents are most connected to my memories?"
uv run ok graph cypher "MATCH (d:Doc)-[:HAS_CHUNK]->(c:Chunk)<-[:DerivedFrom]-(m:MemoryNote) RETURN d.path, count(m) as memory_count ORDER BY memory_count DESC" --json | \
  jq -r '.[] | "Document: \(."d.path" | split("/") | .[-1])\nConnected Memories: \(."memory_count")\n---"'
```

**Example Output:**

```json
[
  {"t.name": "nlp", "memories": ["m-20250919-283cb946", "m-20250919-853c3ef2", "m-20250919-375470ed", "m-20250919-d88b47ef", "m-20250919-4fddc5a9", "m-20250919-393e18dc", "m-20250919-9416162a"]},
  {"t.name": "transformer", "memories": ["m-20250919-d88b47ef", "m-20250919-4fddc5a9"]},
  {"t.name": "architecture", "memories": ["m-20250919-375470ed", "m-20250919-393e18dc", "m-20250919-9416162a"]}
]
```

**Why This Matters:** Graph queries reveal **knowledge connections** - agents can discover related concepts and trace knowledge provenance!

### **5. FILE-BASED DISCOVERY: Leverage Hierarchical Structure**

```bash
# "What documents do I have in different categories, and what memories connect to them?"
find ~/.ok/store/normalized -name "*.md" | head -1 | while read doc; do
  echo "=== Document: $doc ==="
  basename "$doc" | sed 's/\.[^.]*$//' | \
  xargs -I {} uv run ok graph cypher "MATCH (d:Doc {id: '{}'})-[:HAS_CHUNK]->(c:Chunk)<-[:DerivedFrom]-(m:MemoryNote) RETURN m.id, m.text" --json | \
  jq -r '.[] | "Memory: \(."m.id")\n\(."m.text")\n---"'
done
```

**Example Output:**

```
=== Document: /home/ubuntu/.ok/store/normalized/43411d2b03b695e1.ok.md ===
Memory: m-20250919-9416162a
Transformers and BERT represent a paradigm shift in NLP: transformers use self-attention for parallel processing, while BERT leverages bidirectional context through pre-training on large corpora. Both architectures avoid the sequential limitations of RNNs.
---
```

**Why This Matters:** File-based design enables **shell command composition** - agents can combine `find`, `xargs`, and OpenKL commands for powerful knowledge discovery!

### **6. CROSS-REFERENCE: Find Related Memories**

```bash
# "Do I have memories that might contradict or complement each other?"
uv run ok graph cypher "MATCH (m1:MemoryNote)-[:HasTopic]->(t:Topic)<-[:HasTopic]-(m2:MemoryNote) WHERE m1.id <> m2.id RETURN t.name, collect(m1.id) as memories" --json | \
  jq -r '.[] | "Topic: \(."t.name")\nMemories: \(."memories" | join(", "))\n---"'
```

**Example Output:**

```json
[
  {"t.name": "nlp", "memories": ["m-20250919-283cb946", "m-20250919-853c3ef2", "m-20250919-375470ed", "m-20250919-d88b47ef", "m-20250919-4fddc5a9", "m-20250919-393e18dc", "m-20250919-9416162a"]},
  {"t.name": "transformer", "memories": ["m-20250919-d88b47ef", "m-20250919-4fddc5a9"]},
  {"t.name": "architecture", "memories": ["m-20250919-375470ed", "m-20250919-393e18dc", "m-20250919-9416162a"]}
]
```

**Why This Matters:** All 7 memories share the "nlp" topic, and we can see which memories are related through "transformer" and "architecture" topics!

---

## 🔧 **Distillation Prompts**

OpenKL provides standardized prompts for different types of memory distillation. These prompts are designed to work with any LLM and guide the agent in creating high-quality, structured memories.

### **Available Prompt Types**

- `extract-facts` - Extract key facts and definitions
- `identify-patterns` - Identify recurring patterns and themes
- `summarize-insights` - Create concise summaries
- `extract-relationships` - Find connections between concepts
- `extract-entities` - Identify important entities and concepts
- `memory-synthesis` - Synthesize comprehensive memory notes

### **Using Distillation Prompts**

```bash
# List all available prompts
uv run ok distill prompts

# Get a specific prompt
uv run ok distill get-prompt memory-synthesis

# Use in your agent workflow
PROMPT=$(uv run ok distill get-prompt memory-synthesis)
# Your agent evaluates the prompt with an LLM
# Then creates memory with: ok distill create "distilled_content" "source_citations"
```

### **Python Integration Example**

```python
import subprocess
import json

def distill_knowledge(search_query, source_citations):
    """Distill knowledge using OpenKL prompts."""

    # 1. Search for information
    result = subprocess.run([
        "uv", "run", "ok", "search", search_query, "--json"
    ], capture_output=True, text=True)

    search_results = json.loads(result.stdout)

    # 2. Create citations
    for item in search_results[:3]:  # Top 3 results
        subprocess.run([
            "uv", "run", "ok", "cite", "make", item["id"],
            "--retention-class", "durable",
            "--tags", "agent-generated"
        ])

    # 3. Get distillation prompt
    prompt_result = subprocess.run([
        "uv", "run", "ok", "distill", "get-prompt", "memory-synthesis"
    ], capture_output=True, text=True)

    prompt = prompt_result.stdout

    # 4. Use prompt with your LLM (your implementation)
    distilled_content = your_llm_call(prompt, search_results)

    # 5. Create memory with provenance
    citation_ids = [item["id"] for item in search_results[:3]]
    subprocess.run([
        "uv", "run", "ok", "distill", "create",
        distilled_content,
        ",".join(citation_ids),
        "--tags", "agent-distilled",
        "--topics", "ai-generated"
    ])

    return distilled_content
```

---

## 🔧 **Using xargs with OpenKL**

When using `xargs` with OpenKL commands, use `uv run ok` instead of just `ok`:

```bash
# Correct way to use xargs
uv run ok search "transformer" --json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer"

# Alternative: Use PATH export
export PATH="$HOME/.local/bin:$PATH"
ok search "transformer" --json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} ok cite make {} --retention-class durable --tags "transformer"
```

---

## 🎯 **Why Citations Matter for AI Agents**

### **1. Reproducibility**

- Every AI claim can be traced back to its source
- Humans can verify agent reasoning
- Enables debugging and improvement

### **2. Context Management**

- Agents can reference sources without overwhelming context
- Enables working with large documents efficiently
- Supports incremental knowledge building

### **3. Trust & Transparency**

- Provides audit trail for AI decisions
- Enables explainable AI reasoning
- Builds confidence in agent capabilities

### **4. Learning & Improvement**

- Agents can build on verified knowledge
- Enables knowledge graph construction
- Supports continuous learning workflows

---

## 🚀 **Best Practices**

1. **Always create citations** for important findings
2. **Use retention classes** appropriately (durable for important, ephemeral for temporary)
3. **Tag citations** for easy discovery and management
4. **Verify citations** regularly to ensure integrity
5. **Use distillation** to synthesize knowledge with full provenance
6. **Leverage graph queries** to discover connections
7. **Combine file-based and graph-based** approaches for maximum power

# OpenKL Demo: AI Agent Knowledge Management

This demo showcases OpenKL's core capabilities through realistic AI agent workflows, demonstrating file-based tools + graph-aware retrieval + **citations for reproducible AI reasoning**.

## 🎯 **Key Value Propositions**

1. **File-Based Design**: Hierarchical file structure enables advanced shell command composition
2. **Graph-Aware Retrieval**: Connection-aware knowledge discovery and synthesis
3. **Reproducible Citations**: Traceable, verifiable provenance for AI reasoning
4. **Agent-Driven Distillation**: Standardized prompts for knowledge synthesis

---

## Demo Playground Setup

Let's build a realistic knowledge base to demonstrate OpenKL's capabilities:

```bash
# 1. Initialize OpenKL
uv run ok doctor

# 2. Ingest foundational papers
uv run ok store arxiv 1706.03762  # "Attention Is All You Need" - Transformer paper
uv run ok store arxiv 1810.04805  # "BERT: Pre-training of Deep Bidirectional Transformers"

# 3. Add core memory insights
uv run ok mem add "Transformers use self-attention mechanisms for parallel processing, enabling better long-range dependencies than RNNs. The architecture consists of encoder-decoder layers with multi-head attention." \
  --tags "transformer,attention,architecture" --topics "nlp,deep-learning"

uv run ok mem add "BERT uses bidirectional context for better language understanding by pre-training on large text corpora and fine-tuning on specific tasks." \
  --tags "bert,bidirectional,pre-training" --topics "nlp,bert"

uv run ok mem add "Self-attention allows the model to attend to different positions in the input sequence simultaneously, making it more parallelizable than RNNs." \
  --tags "self-attention,parallelization" --topics "nlp,architecture"

uv run ok mem add "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions." \
  --tags "multi-head,attention,representation" --topics "nlp,transformer"

uv run ok mem add "Positional encoding is added to input embeddings to give the model information about the position of words in the sequence." \
  --tags "positional-encoding,embeddings" --topics "nlp,transformer"

# 4. Create citations for key findings (demonstrates provenance tracking)
uv run ok cite make 43411d2b03b695e1#chunk0036 --retention-class durable --tags "transformer,attention"
uv run ok cite make 831514a53d5ea432#chunk0000 --retention-class durable --tags "bert,pre-training"

# 5. Create distilled memory with provenance (demonstrates knowledge synthesis)
uv run ok distill create "Transformers and BERT represent a paradigm shift in NLP: transformers use self-attention for parallel processing, while BERT leverages bidirectional context through pre-training on large corpora. Both architectures avoid the sequential limitations of RNNs." \
  "43411d2b03b695e1#chunk0036,831514a53d5ea432#chunk0000" \
  --tags "transformer,bert,nlp-paradigm" --topics "nlp,architecture"

# 6. Verify our knowledge base
uv run ok graph stats
```

**Expected Output:**

```text
Graph Statistics
C_count: 125
M_count: 7
D_count: 2
E_count: 0
T_count: 4
R_count: 2
```

**What We Built:**

- **2 research papers** ingested and chunked (125 chunks)
- **7 memory notes** with structured insights
- **2 citations** linking memories to source documents
- **1 distilled memory** with full provenance tracking
- **4 topics** for hierarchical organization

---

## 🚀 **Core Workflows**

### **1. REPRODUCIBLE AI REASONING: Citations in Action**

```bash
# Search for information and create citations
# Using jq (preferred):
uv run ok search "transformer architecture" --json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer,architecture"

# Fallback without jq:
# uv run ok search "transformer architecture" --json | grep -o '"id": "[^"]*"' | head -3 | cut -d'"' -f4 | \
#   xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer,architecture"

# Verify citations (demonstrates integrity checking)
ok cite list

# Open a citation to see full context and provenance
ok cite open 43411d2b03b695e1#chunk0036
```

**Example Output:**

```text
Citation: 43411d2b03b695e1#chunk0036
File: /home/ubuntu/.ok/store/normalized/43411d2b03b695e1.ok.md
Type: chunk
Status: verified
Quote:
>>>> (begin cite) <<<<
the Section 22 development set, all other parameters remained unchanged from the
English-to-German base translation model. During inference, we 9 Table 4: The
Transformer generalizes well to English constituency parsing...
>>>> (end cite) <<<<
```

**Why This Matters:** Citations provide **reproducible provenance** - agents can trace every claim back to its source, enabling auditable AI reasoning!

### **2. CONTEXT WINDOW MANAGEMENT: Smart Citation Usage**

```bash
# Instead of including entire documents, agents can cite specific sections
# Using jq (preferred):
echo "Based on my knowledge base, here are the key insights about transformer architecture:

$(uv run ok search "transformer" --json | jq -r '.[] | "- \(.text) (okcite://\(.id))"')

These insights are grounded in the following sources:
$(ok cite list --json | jq -r '.[] | "\(.id): \(.status)"' | head -3)"

# Fallback without jq:
# echo "Based on my knowledge base, here are the key insights about transformer architecture:
#
# $(uv run ok search "transformer" --json | grep -o '"text": "[^"]*"' | cut -d'"' -f4 | head -3 | sed 's/^/- /')
#
# These insights are grounded in the following sources:
# $(ok cite list | grep "transformer\|architecture" | head -3)"
```

**Example Output:**

```
Based on my knowledge base, here are the key insights about transformer architecture:

- Transformers use self-attention mechanisms for parallel processing... (okcite://m-20250919-283cb946)
- Self-attention allows the model to attend to different positions... (okcite://m-20250919-375470ed)
- Multi-head attention allows the model to jointly attend... (okcite://m-20250919-d88b47ef)

These insights are grounded in the following sources:
43411d2b03b695e1#chunk0036: verified
831514a53d5ea432#chunk0000: verified
m-20250919-aaf7c399: verified
```

**Why This Matters:** Citations enable **context-efficient responses** - agents can reference specific sources without overwhelming the context window!

### **3. KNOWLEDGE SYNTHESIS: Agent-Driven Distillation**

```bash
# 1. Search for relevant information
uv run ok search "transformer architecture" --json

# 2. Create citations for key findings
uv run ok search "transformer architecture" --json | jq -r '.[] | .id' | head -3 | \
  xargs -I {} uv run ok cite make {} --retention-class durable --tags "transformer,architecture"

# 3. Get distillation prompt for your LLM
uv run ok distill get-prompt memory-synthesis

# 4. Use the prompt with your LLM to distill content
# (Your agent evaluates the prompt and generates distilled content)
# The prompt templates will be `MCP Prompt` or part of `Agents.md`, too.

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
  {
    "m.id": "m-20250919-e4fe4186",
    "c.id": "831514a53d5ea432#chunk0000"
  },
  {
    "m.id": "m-20250919-e4fe4186",
    "c.id": "43411d2b03b695e1#chunk0036"
  },
  {
    "m.id": "m-20250919-efe68724",
    "c.id": "831514a53d5ea432#chunk0000"
  },
  {
    "m.id": "m-20250919-efe68724",
    "c.id": "43411d2b03b695e1#chunk0036"
  }
]
```

**Why This Matters:** Distillation creates **knowledge graphs** - agents can synthesize insights and OpenKL automatically tracks provenance through `DerivedFrom` relationships!

### **4. FILE-BASED DISCOVERY: Leverage Hierarchical Structure**

```bash
# "What documents do I have in different categories, and what memories connect to them?"
find ~/.ok/store/normalized -name "*.md" | head -1 | while read doc; do
  echo "=== Document: $doc ==="
  doc_id=$(basename "$doc" | sed 's/\.ok\.md$//')
  echo "Document ID: $doc_id"
  uv run ok graph cypher "MATCH (d:Doc {id: '$doc_id'})-[:HAS_CHUNK]->(c:Chunk)<-[:DerivedFrom]-(m:MemoryNote) RETURN m.id" --json | \
  jq -r '.[] | "Memory: \(."m.id")"'
done
```

**Example Output:**

```text
=== Document: /home/ubuntu/.ok/store/normalized/43411d2b03b695e1.ok.md ===
Document ID: 43411d2b03b695e1
Memory: m-20250919-efe68724
Memory: m-20250919-e4fe4186
```

**Why This Matters:** File-based design enables **shell command composition** - agents can combine `find`, `xargs`, and OpenKL commands for powerful knowledge discovery!

### **5. GRAPH-AWARE RETRIEVAL: Connection Discovery**

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
Topic: architecture
Memories: m-20250919-e4fe4186, m-20250919-f99d19ab
---
Topic: nlp
Memories: m-20250919-4adbf749, m-20250919-f99d19ab, m-20250919-39729855, m-20250919-663f1552, m-20250919-e4fe4186
---
Topic: transformer
Memories: m-20250919-663f1552, m-20250919-39729855
---
```

**Why This Matters:** Graph queries reveal **knowledge connections** - agents can discover related concepts and trace knowledge provenance across documents!

---

## 🔧 **Advanced Agent Workflows**

### **Memory Management with Citations**

```bash
# Update a memory and see how citations adapt
uv run ok mem update m-20250919-efe68724 --text "Transformers use self-attention mechanisms for parallel processing, enabling better long-range dependencies than RNNs. The architecture consists of encoder-decoder layers with multi-head attention. This represents a fundamental shift from sequential to parallel processing in NLP."

# Check how citations are affected
uv run ok cite open m-20250919-efe68724
```

### **Citation Lifecycle Management**

```bash
# List all citations with their status
uv run ok cite list

# Clean up old citations
uv run ok cite gc

# Verify citation integrity
uv run ok cite verify 43411d2b03b695e1#chunk0036
```

### **Distillation Prompt Library**

```bash
# List available distillation prompts
uv run ok distill prompts

# Get specific prompt for your use case
uv run ok distill get-prompt extract-facts
uv run ok distill get-prompt identify-patterns
uv run ok distill get-prompt memory-synthesis
```

---

## 🎯 **Why Citations Matter for AI Agents**

### **1. Reproducibility**

- Every AI claim can be traced back to its source
- Humans can verify agent reasoning
- Enables debugging and improvement

### **2. Context Management**

- Agents/Sub-agents can reference sources without overwhelming context
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

## 🚀 **Next Steps**

1. **Try the workflows above** - each demonstrates a key OpenKL capability
2. **Explore the graph** - use `ok graph cypher` to discover connections
3. **Create your own citations** - build a knowledge base for your domain
4. **Integrate with your agents** - use OpenKL as a knowledge layer

For detailed agent integration, see [examples/agents.md](examples/agents.md).

For technical design, see [rfcs/0000-openkl-design.md](rfcs/0000-openkl-design.md).

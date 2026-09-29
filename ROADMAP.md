# learn-ai — Roadmap

> **Purpose of this project:** learn **how to build an LLM application from first
> principles** — not just how to wire APIs together. Every concept is derived from
> the problem it solves *before* reaching for a library. We do not skip concepts to
> get to working code faster.

**Frozen:** 2026-09-30

---

## Current position

```text
RAG → 1. Information Retrieval → before embeddings
```

Next lesson: **classical Information Retrieval**. Start by searching a collection of
text with keywords, then derive **inverted index → TF-IDF → BM25 → precision/recall**
from the problems we hit. This establishes *why* semantic search and embeddings are
necessary — so embeddings are never treated as magic.

Deliberately **not touched yet:** embeddings, pgvector, Pinecone, FAISS, chunking
code, rerankers. Understand why each exists first.

---

## Layer 1 — LLM Application Runtime ✅ DONE

```text
✅  1. Conversation
✅  2. Generation
✅  3. Streaming / SSE
✅  4. Event architecture
✅  5. LLM provider abstraction
✅  6. GenerationRunner / orchestration
✅  7. Tool architecture
✅  8. Tool execution
✅  9. Tool calling loop
✅ 10. Cancellation
✅ 11. PromptBuilder
✅ 12. Conversation continuation / history
```

### Conceptual lessons locked in (the point of the layer)

- **Conversation ≠ Generation**
- **Generation ≠ assistant message**
- **State ≠ events**
- **Runner orchestrates; services provide capabilities**
- **Provider protocol ≠ application protocol**
- **Tool ≠ ToolExecution ≠ ToolResult**
- **Cancellation request ≠ cancellation fact**
- **Prompt assembly ≠ persistence**
- **LLMSession owns provider-specific message plumbing**

> Deferred runtime seams (intentionally left, revisit when relevant — not part of the
> learning path, just honest debt): client doesn't render `tool_started`/`tool_finished`
> yet; `PromptBuilder` truncation/`budget` unimplemented; tool_use/tool_result not
> persisted; services leak `HTTPException`; no user/auth scoping; conversation titles;
> unused `EventType.MESSAGE`.

---

## Layer 2 — RAG (current milestone)

We have **not** implemented RAG yet. Progress through the steps in order.

### 👉 1. Information Retrieval — **WE ARE HERE**

Retrieval *without* AI first.

```text
Query → Search → Relevant information
```

- What is Information Retrieval?
- What is a query?
- What is relevance?
- Keyword search
- Inverted indexes
- TF-IDF
- BM25
- Precision
- Recall
- Precision vs Recall trade-off
- Why keyword search works
- Where keyword search breaks  ← this is the problem semantic search solves

### ⬜ 2. Documents → Chunks

> Why can't we just retrieve entire documents?

```text
Document → Chunks
```

Document representation · chunking · chunk size · overlap · why boundaries matter ·
fixed-size · sentence/paragraph · recursive · semantic chunking · chunk metadata.

Key distinction: **Document ≠ Chunk** (document = source; chunk = unit we retrieve).

### ⬜ 3. Embeddings

Only after understanding why lexical search isn't enough.

```text
Text → Embedding model → Vector
```

What an embedding represents · embedding space · dimensions · semantic similarity ·
cosine similarity · dot product · distance metrics · why similar meanings cluster ·
limitations. **Semantic search enters here.**

### ⬜ 4. Vector Search / ANN

```text
10,000,000 chunks → 10,000,000 vectors → searching all of them is expensive
```

Exact NN · approximate NN · vector indexes · ANN · HNSW · IVF ·
accuracy/latency/memory trade-offs. *Only then* introduce pgvector / FAISS / Pinecone.

### ⬜ 5. Basic Retrieval Pipeline

```text
User Query → Embedding → Vector Search → Top-K Chunks
```

`k` · similarity threshold · retrieval latency · empty results · duplicate results ·
relevance problems. Yields a **basic semantic RAG system**.

### ⬜ 6. Reranking

> The nearest vectors aren't necessarily the best context.

```text
Query → Retrieve 20 → Rerank → Keep 5
```

Why reranking exists · bi-encoder vs cross-encoder · reranker models ·
accuracy vs latency · top-K retrieval vs top-N context.

### ⬜ 7. Hybrid Search

Some queries (e.g. `"React useOptimistic API"`) need exact terminology.

```text
BM25 / keyword  +  Vector search  →  Hybrid retrieval
```

Lexical vs semantic retrieval · score normalization · reciprocal rank fusion ·
when each beats the other.

### ⬜ 8. Metadata Filtering

```text
department=engineering · product=payments · version=v3
Metadata filter → Retrieval → Relevant chunks
```

Metadata · pre-filtering · post-filtering · filter + vector search ·
why metadata is critical in production RAG.

### ⬜ 9. Context Assembly / PromptBuilder integration

Our existing architecture comes back and evolves:

```text
Conversation ──────┐
Retrieved Chunks ──┤
System Prompt ─────┤→ PromptBuilder → Prompt
```

How much context to include · ordering chunks · context windows · context pollution ·
source attribution · citations · duplicate context · **prompt injection from retrieved
documents**. RAG becomes part of the assistant, not just a search engine.

### ⬜ 10. Evaluation — **not skipped**

```text
Recall@K · Precision@K · MRR · NDCG · Hit Rate
```

Distinguish **retrieval quality ≠ generation quality**:
`good docs + bad answer` is a different bug from `bad docs + good-looking answer`.

### ⬜ 11. Production RAG

Indexing pipelines · document updates · deletion · re-indexing · embedding model
changes · versioning · caching · latency · observability · cost · stale embeddings ·
duplicate documents · access control. **After** the fundamentals.

---

## Layer 3 — Memory

```text
RAG → Users → Memory
```

Specifically understand **why memory is not simply RAG**.

```text
User
 ├── Conversations
 └── Memories
```

Short-term · conversation memory · long-term · memory extraction · memory retrieval ·
memory updates · conflicting memories · forgetting/deletion · user-level vs
conversation-level. **This is where introducing the `User` model becomes justified.**

---

## Layer 4 — System Maturity

### ⬜ Multi-provider
Provider abstraction · model configuration · capability differences · fallback ·
provider-specific features · why "one universal interface" can become leaky.

### ⬜ Observability
Instrument the whole pipeline:

```text
Generation
 ├── LLM latency
 ├── TTFT
 ├── tokens
 ├── tool latency
 ├── retrieval latency
 ├── retrieved chunks
 ├── model/provider
 └── errors
```

---

## The whole journey

```text
LLM APPLICATION RUNTIME  ✅ (12/12)
        ↓
RAG                      👉 step 1 of 11 (Information Retrieval)
        ↓
MEMORY                   ⬜
        ↓
SYSTEM MATURITY          ⬜ (multi-provider, observability)
```
